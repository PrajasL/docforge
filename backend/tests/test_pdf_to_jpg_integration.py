import asyncio
import io
import os
import subprocess
import sys
import time
import uuid
import zipfile

import pypdf
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

import app.core.database as db_core
from app.core.storage import S3StorageBackend, set_storage_backend
from app.jobs.models import JobStatus
from app.jobs.service import JobService
from app.main import app
from app.workers.tasks import process_job_task
from tests.test_celery_redis_integration import is_minio_available, is_redis_available


def create_test_pdf(page_count: int = 3) -> bytes:
    """Creates a sample multi-page PDF with distinct page dimensions."""
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        writer.add_blank_page(width=200 + (i * 50), height=300 + (i * 50))
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_pdf_to_jpg_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for PDF to JPG with real Redis, MinIO, PostgreSQL, and Celery worker.
    Verifies that:
    1. A pdf_to_jpg job created and started via API is processed by the background worker.
    2. Input file is downloaded from MinIO.
    3. Every page is converted into a high-quality JPG image.
    4. Output is packaged into a ZIP archive and uploaded to MinIO.
    5. Downloaded ZIP contains exactly 3 valid JPEGs.
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

            # Step A: Create job
            pdf_bytes = create_test_pdf(3)
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "pdf_to_jpg",
                    "files": [
                        {
                            "name": "photo_doc.pdf",
                            "size": len(pdf_bytes),
                            "content_type": "application/pdf",
                        }
                    ],
                    "config": {
                        "dpi": 150,
                        "quality": 85,
                        "output_filename": "photo_doc_gallery.zip",
                    },
                },
                headers=headers,
            )
            assert create_resp.status_code == 201
            create_data = create_resp.json()["data"]
            job_id = create_data["job"]["id"]
            uploads = create_data["uploads"]
            assert len(uploads) == 1
            file_id = uploads[0]["file_id"]

            # Step B: Upload file via API
            up_resp = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file_id}",
                content=pdf_bytes,
                headers={"Content-Type": "application/pdf", "X-Session-Id": session_id},
            )
            assert up_resp.status_code == 200

            # Step C: Start job
            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "dpi": 150,
                        "quality": 85,
                        "output_filename": "photo_doc_gallery.zip",
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
                    if job:
                        last_status = job.status
                        if job.status == JobStatus.COMPLETED:
                            completed = True
                            break
                        elif job.status == JobStatus.FAILED:
                            pytest.fail(f"Job failed unexpectedly: {job.error_message}")

            assert completed, f"Job timed out before completion. Final status was {last_status}"

            # Step F: Validate result file metadata
            async with db_core.AsyncSessionLocal() as session:
                final_job = await JobService.get_job(session, job_id)
                res_meta = final_job.result_file
                assert res_meta is not None
                assert res_meta["original_name"] == "photo_doc_gallery.zip"
                assert res_meta["file_count"] == 3
                assert res_meta["content_type"] == "application/zip"
                storage_key = res_meta["storage_key"]

            # Step G: Download output from MinIO and inspect ZIP
            output_bytes = await real_storage.download(
                key=storage_key,
                bucket=real_storage.outputs_bucket,
            )
            assert len(output_bytes) > 0

            with zipfile.ZipFile(io.BytesIO(output_bytes), "r") as z:
                names = z.namelist()
                assert len(names) == 3
                assert names == ["page_01.jpg", "page_02.jpg", "page_03.jpg"]
                for n in names:
                    img_data = z.read(n)
                    assert img_data.startswith(b"\xff\xd8\xff")
                    with Image.open(io.BytesIO(img_data)) as img:
                        assert img.format == "JPEG"
                        assert img.width > 0
                        assert img.height > 0

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
