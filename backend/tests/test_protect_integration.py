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
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=400)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_protect_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Protect PDF with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. A Protect PDF job created and started via the API is queued onto Redis.
    2. Passwords are NEVER written to PostgreSQL job metadata or result metadata.
    3. An actual Celery worker process picks up and executes the task using ephemeral Redis secrets.
    4. Input file is read from real MinIO storage.
    5. Document is encrypted using AES-256.
    6. Result PDF is uploaded to MinIO and marked COMPLETED in PostgreSQL.
    7. The downloaded PDF opens cleanly ONLY when supplying the correct password.
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
        protect_password = "SecureWorkerPassword_987!"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-protect-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "protect",
                    "files": [
                        {"name": "financial_doc.pdf", "size": len(pdf_bytes), "content_type": "application/pdf"}
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

            # Step C: Start job with Protect PDF config
            from app.workers.tasks import process_job_task

            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "password": protect_password,
                        "confirm_password": protect_password,
                        "output_filename": "protected_financial.pdf",
                    }
                },
                headers={"X-Session-Id": session_id},
            )
            assert start_resp.status_code == 200

            # Step D: Verify password is NOT in database job.config
            async with db_core.AsyncSessionLocal() as session:
                queued_job = await JobService.get_job(session, job_id)
                assert queued_job is not None
                assert "password" not in queued_job.config
                assert "confirm_password" not in queued_job.config

            # Step E: Queue task to Celery on Redis
            process_job_task.apply_async(args=[job_id])

            # Step F: Poll PostgreSQL for COMPLETED status
            start_time = time.time()
            completed = False
            last_status = None

            while time.time() - start_time < 20:
                await asyncio.sleep(0.5)
                async with db_core.AsyncSessionLocal() as session:
                    job = await JobService.get_job(session, job_id)
                    if job:
                        last_status = job.status
                        if job.status == JobStatus.COMPLETED:
                            completed = True
                            break
                        elif job.status == JobStatus.FAILED:
                            pytest.fail(f"Job failed on worker with error: {job.error_message}")

            if not completed:
                worker_proc.terminate()
                stdout, stderr = worker_proc.communicate(timeout=3)
                print("WORKER STDOUT:\n", stdout.decode("utf-8", errors="replace"))
                print("WORKER STDERR:\n", stderr.decode("utf-8", errors="replace"))

            assert completed, f"Job timed out before completion. Final status was {last_status}"

            # Step G: Validate result file metadata in database (No password stored)
            async with db_core.AsyncSessionLocal() as session:
                final_job = await JobService.get_job(session, job_id)
                res_meta = final_job.result_file
                assert res_meta is not None
                assert res_meta["original_name"] == "protected_financial.pdf"
                assert res_meta["page_count"] == 3
                assert res_meta["is_encrypted"] is True
                assert res_meta["encryption_algorithm"] == "AES-256"
                assert "password" not in res_meta
                assert "password" not in final_job.config
                storage_key = res_meta["storage_key"]

            # Step H: Download and inspect output PDF from MinIO
            output_bytes = await real_storage.download(
                key=storage_key,
                bucket=real_storage.outputs_bucket,
            )
            assert len(output_bytes) > 0

            # Step I: Validate encryption behavior
            reader = pypdf.PdfReader(io.BytesIO(output_bytes))
            assert reader.is_encrypted is True

            # Wrong password fails
            dec_wrong = reader.decrypt("WrongPassword123")
            assert dec_wrong == 0

            # Correct password decrypts
            reader_correct = pypdf.PdfReader(io.BytesIO(output_bytes))
            dec_correct = reader_correct.decrypt(protect_password)
            assert dec_correct != 0
            assert len(reader_correct.pages) == 3

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
