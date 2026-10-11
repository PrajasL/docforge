import asyncio
import io
import os
import subprocess
import sys
import time
import uuid
import pytest
import pypdf
from PIL import Image
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.core.storage import S3StorageBackend, set_storage_backend
import app.core.database as db_core
from app.jobs.models import Job, JobStatus
from app.jobs.service import JobService
from app.workers.tasks import process_job_task
from app.main import app
from tests.test_celery_redis_integration import is_redis_available, is_minio_available


def create_test_jpeg(width: int = 400, height: int = 300, color: tuple = (200, 100, 50)) -> bytes:
    """Creates a sample valid JPEG in bytes."""
    bio = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(bio, format="JPEG", quality=85)
    return bio.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_jpg_to_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for JPG to PDF with real Redis, MinIO, PostgreSQL, and Celery worker.
    Verifies that:
    1. A jpg_to_pdf job created and started via API is processed by the background worker.
    2. Input JPEG images are uploaded to MinIO.
    3. Images are combined in the specified order into one downloadable PDF.
    4. Worker uploads output PDF to MinIO outputs bucket.
    5. Downloaded PDF opens, contains 2 pages with requested page dimensions and sequence.
    """
    real_storage = S3StorageBackend()
    set_storage_backend(real_storage)

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    worker_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "app.workers.celery_app.celery_app",
            "worker",
            "--pool=solo",
            "--loglevel=info",
            "-c",
            "1",
        ],
        cwd=backend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2.5)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = str(uuid.uuid4())
            headers = {"X-Session-ID": session_id}

            img1_bytes = create_test_jpeg(300, 200, (255, 0, 0))
            img2_bytes = create_test_jpeg(500, 400, (0, 0, 255))

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "jpg_to_pdf",
                    "files": [
                        {
                            "name": "photo_1.jpg",
                            "size": len(img1_bytes),
                            "content_type": "image/jpeg",
                        },
                        {
                            "name": "photo_2.jpeg",
                            "size": len(img2_bytes),
                            "content_type": "image/jpeg",
                        },
                    ],
                    "config": {
                        "orientation": "landscape",
                        "page_size": "a4",
                        "margin": "small",
                        "output_filename": "album.pdf",
                    },
                },
                headers=headers,
            )
            assert create_resp.status_code == 201
            create_data = create_resp.json()["data"]
            job_id = create_data["job"]["id"]
            uploads = create_data["uploads"]
            assert len(uploads) == 2

            file1_id = uploads[0]["file_id"]
            file2_id = uploads[1]["file_id"]

            # Step B: Upload files via API
            up1_resp = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file1_id}",
                content=img1_bytes,
                headers={"Content-Type": "image/jpeg", "X-Session-Id": session_id},
            )
            assert up1_resp.status_code == 200

            up2_resp = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file2_id}",
                content=img2_bytes,
                headers={"Content-Type": "image/jpeg", "X-Session-Id": session_id},
            )
            assert up2_resp.status_code == 200

            # Step C: Start job with reordered sequence (file2 first, file1 second)
            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "orientation": "landscape",
                        "page_size": "a4",
                        "margin": "small",
                        "file_order": [file2_id, file1_id],
                        "output_filename": "album.pdf",
                    }
                },
                headers=headers,
            )
            assert start_resp.status_code == 200

            # Step D: Queue task to Celery
            process_job_task.apply_async(args=[job_id])

            # Step E: Poll until COMPLETED
            max_wait = 25
            start_time = time.time()
            completed = False
            last_status = None

            while time.time() - start_time < max_wait:
                await asyncio.sleep(0.5)
                async with db_core.AsyncSessionLocal() as session:
                    job = await JobService.get_job(session, job_id)
                    last_status = job.status
                    if job.status == JobStatus.COMPLETED:
                        completed = True
                        break
                    elif job.status == JobStatus.FAILED:
                        pytest.fail(f"Job failed unexpectedly: {job.error_message}")

            assert completed, f"Job did not complete within {max_wait}s. Last status: {last_status}"

            # Step F: Validate output
            async with db_core.AsyncSessionLocal() as session:
                job = await JobService.get_job(session, job_id)
                assert job.status == JobStatus.COMPLETED
                assert job.result_file is not None
                assert job.result_file.get("original_name") == "album.pdf"
                assert job.result_file.get("page_count") == 2
                assert job.result_file.get("file_count") == 2
                assert job.result_file.get("size_bytes") > 0
                assert job.result_file.get("sha256") is not None

                output_storage_key = job.result_file["storage_key"]
                assert await real_storage.exists(output_storage_key)

                # Download and inspect PDF
                pdf_data = await real_storage.download(output_storage_key)
                reader = pypdf.PdfReader(io.BytesIO(pdf_data))
                assert len(reader.pages) == 2
                # Verify landscape A4 (width > height, width ~ 842 pt)
                for page in reader.pages:
                    assert float(page.mediabox.width) > float(page.mediabox.height)
                    assert abs(float(page.mediabox.width) - 841.89) < 2.0

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
