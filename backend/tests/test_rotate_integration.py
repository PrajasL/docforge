import asyncio
import io
import os
import subprocess
import sys
import time
import uuid
import pytest
import pypdf
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.core.storage import S3StorageBackend, set_storage_backend
import app.core.database as db_core
from app.jobs.models import Job, JobStatus
from app.jobs.service import JobService
from app.main import app
from tests.test_celery_redis_integration import is_redis_available, is_minio_available


def create_test_pdf(page_count: int = 3) -> bytes:
    """Creates a sample multi-page PDF."""
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        writer.add_blank_page(width=100 + i * 20, height=200 + i * 20)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_rotate_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Rotate PDF with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. A Rotate PDF job created and started via the API is queued onto Redis.
    2. An actual Celery worker process picks up and executes the task.
    3. Input file is read from real MinIO storage.
    4. Selected pages are rotated losslessly according to specified rotation parameters.
    5. Result PDF is uploaded to MinIO and marked COMPLETED in PostgreSQL.
    6. Result metadata accurately records rotated page count and rotation angle.
    7. The downloaded PDF opens cleanly and has the exact rotation angles applied.
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

        pdf_bytes = create_test_pdf(3)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-rotate-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "rotate",
                    "files": [
                        {"name": "original_doc.pdf", "size": len(pdf_bytes), "content_type": "application/pdf"}
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

            # Step C: Start job rotating pages 1 and 3 by 90 degrees
            from app.workers.tasks import process_job_task

            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "angle": 90,
                        "pages": "1, 3",
                        "output_filename": "rotated_result.pdf",
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

            assert completed is True, f"Rotate job did not complete within timeout. Last status: {last_status}"

            # Step F: Verify job details and rotation metadata
            async with db_core.AsyncSessionLocal() as session:
                job = await JobService.get_job(session, job_id)
                assert job.progress == 100
                res = job.result_file
                assert res is not None
                assert res["original_name"] == "rotated_result.pdf"
                assert res["content_type"] == "application/pdf"
                assert res["page_count"] == 3
                assert res["rotated_pages_count"] == 2
                assert res["rotation_angle"] == 90
                assert res["size_bytes"] > 0

                # Step G: Download and inspect output PDF from MinIO
                output_key = res["storage_key"]
                assert await real_storage.exists(output_key) is True
                rotated_bytes = await real_storage.download(output_key)

                # Step H: Verify rotation applied on pages
                reader = pypdf.PdfReader(io.BytesIO(rotated_bytes))
                assert len(reader.pages) == 3
                assert reader.pages[0].rotation == 90
                assert reader.pages[1].rotation == 0
                assert reader.pages[2].rotation == 90

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
