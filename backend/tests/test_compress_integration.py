import asyncio
import io
import os
import subprocess
import sys
import time
import uuid
import pytest
import pikepdf
from PIL import Image
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.core.storage import S3StorageBackend, set_storage_backend
import app.core.database as db_core
from app.jobs.models import Job, JobStatus
from app.jobs.service import JobService
from app.main import app
from tests.test_celery_redis_integration import is_redis_available, is_minio_available


def create_image_test_pdf(width: int = 1000, height: int = 1000) -> bytes:
    """Creates a PDF with a large uncompressed RGB raster image."""
    img = Image.new("RGB", (width, height), color=(60, 120, 180))
    for x in range(0, width, 10):
        for y in range(0, height, 10):
            img.putpixel((x, y), (x % 256, y % 256, 200))
    pdf_stream = io.BytesIO()
    img.save(pdf_stream, "PDF")
    return pdf_stream.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_compress_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Compress PDF with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. A Compress PDF job created and started via the API is queued onto Redis.
    2. An actual Celery worker process picks up and executes the task.
    3. Input file is read from real MinIO storage.
    4. Image downsampling & compression achieves measured size reduction.
    5. Result PDF is uploaded to MinIO and marked COMPLETED in PostgreSQL.
    6. Result metadata accurately records original size, compressed size, and savings percentage.
    7. The downloaded PDF is valid, readable, and preserves page count.
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        await asyncio.sleep(2.0)

        pdf_bytes = create_image_test_pdf(800, 800)
        orig_size = len(pdf_bytes)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-compress-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "compress",
                    "files": [
                        {"name": "high_res_photo.pdf", "size": orig_size, "content_type": "application/pdf"}
                    ],
                    "config": {},
                },
                headers={"X-Session-Id": session_id},
            )
            assert create_resp.status_code == 201
            create_data = create_resp.json()["data"]
            job_id = create_data["job"]["id"]
            uploads = create_data["uploads"]
            assert len(uploads) == 1
            file_id = uploads[0]["file_id"]

            # Step B: Upload file to MinIO via API
            up_resp = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file_id}",
                content=pdf_bytes,
                headers={"X-Session-Id": session_id},
            )
            assert up_resp.status_code == 200

            # Step C: Start job with Maximum compression
            from app.workers.tasks import process_job_task

            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "level": "maximum",
                        "output_filename": "compressed_result.pdf",
                    }
                },
                headers={"X-Session-Id": session_id},
            )
            assert start_resp.status_code == 200

            # Step D: Queue task to Celery on Redis
            process_job_task.apply_async(args=[job_id])

            # Step E: Poll PostgreSQL for COMPLETED status
            start_time = time.time()
            completed = False
            last_status = None

            while time.time() - start_time < 20:
                await asyncio.sleep(0.5)
                async with db_core.AsyncSessionLocal() as session:
                    job = await JobService.get_job(session, job_id)
                    last_status = job.status
                    if job.status == JobStatus.COMPLETED:
                        completed = True
                        break
                    if job.status == JobStatus.FAILED:
                        break

            if not completed:
                worker_proc.terminate()
                stdout, stderr = worker_proc.communicate(timeout=3)
                print("WORKER STDOUT:\n", stdout.decode("utf-8", errors="replace"))
                print("WORKER STDERR:\n", stderr.decode("utf-8", errors="replace"))
                async with db_core.AsyncSessionLocal() as session:
                    job = await JobService.get_job(session, job_id)
                    print("JOB ERROR:", job.error_code, job.error_message, job.error_details)

            assert completed is True, f"Compress job did not complete within timeout. Last status: {last_status}"

            # Step F: Verify job details and compression savings metadata
            async with db_core.AsyncSessionLocal() as session:
                job = await JobService.get_job(session, job_id)
                assert job.progress == 100
                res = job.result_file
                assert res is not None
                assert res["original_name"] == "compressed_result.pdf"
                assert res["content_type"] == "application/pdf"
                assert res["original_size_bytes"] == orig_size
                assert res["size_bytes"] < orig_size
                assert res["savings_bytes"] > 0
                assert res["savings_percentage"] > 0.0
                assert res["is_already_optimal"] is False
                assert res["page_count"] == 1

                # Step G: Download and inspect output PDF from MinIO
                output_key = res["storage_key"]
                assert await real_storage.exists(output_key) is True
                compressed_bytes = await real_storage.download(output_key)
                assert len(compressed_bytes) == res["size_bytes"]

                # Step H: Verify readable PDF structure
                with pikepdf.Pdf.open(io.BytesIO(compressed_bytes)) as out_pdf:
                    assert len(out_pdf.pages) == 1

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
