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
from app.workers.tasks import process_job_task
from app.main import app
from tests.test_celery_redis_integration import is_redis_available, is_minio_available


def create_encrypted_test_pdf(password: str = "TestSecret987!", page_count: int = 3) -> bytes:
    """Creates a password-protected PDF using AES-256."""
    writer = pypdf.PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=400)
    writer.encrypt(user_password=password, algorithm="AES-256")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_unlock_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Unlock PDF with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. An Unlock PDF job created and started via the API is queued onto Redis.
    2. Passwords are NEVER written to PostgreSQL job metadata or result metadata.
    3. An actual Celery worker process picks up and executes the task using ephemeral Redis secrets.
    4. Input file is read from real MinIO storage.
    5. Document is decrypted and re-saved as an unencrypted PDF.
    6. Result PDF is uploaded to MinIO and marked COMPLETED in PostgreSQL.
    7. The downloaded PDF opens cleanly WITHOUT ANY password.
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

        correct_pw = "UnlockE2E_SecretPW!"
        pdf_bytes = create_encrypted_test_pdf(password=correct_pw, page_count=3)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-unlock-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "unlock",
                    "files": [
                        {"name": "encrypted_vault.pdf", "size": len(pdf_bytes), "content_type": "application/pdf"}
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
                headers={"Content-Type": "application/pdf", "X-Session-Id": session_id},
            )
            assert up_resp.status_code == 200

            # Step C: Start job with ephemeral password
            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "password": correct_pw,
                        "output_filename": "clean_vault.pdf",
                    }
                },
                headers={"X-Session-Id": session_id},
            )
            assert start_resp.status_code == 200

            # Step D: Security Check - verify password is NOT in PostgreSQL
            async with db_core.AsyncSessionLocal() as session:
                persisted_job = await JobService.get_job(session, job_id)
                assert persisted_job is not None
                db_config = persisted_job.config or {}
                assert "password" not in db_config
                assert correct_pw not in str(db_config)

            # Step E: Celery task execution
            process_job_task.apply_async(args=[job_id])

            # Step F: Poll until COMPLETED
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

            if not completed:
                worker_proc.terminate()
                stdout, stderr = worker_proc.communicate(timeout=3)
                print("WORKER STDOUT:\n", stdout.decode("utf-8", errors="replace"))
                print("WORKER STDERR:\n", stderr.decode("utf-8", errors="replace"))

            assert completed, f"Job timed out before completion. Final status was {last_status}"

            # Step G: Verify result metadata in PostgreSQL (password never present)
            async with db_core.AsyncSessionLocal() as session:
                final_job = await JobService.get_job(session, job_id)
                res_meta = final_job.result_file
                assert res_meta is not None
                assert res_meta["original_name"] == "clean_vault.pdf"
                assert res_meta["page_count"] == 3
                assert res_meta["is_encrypted"] is False
                assert "password" not in str(res_meta)
                assert "password" not in final_job.config
                storage_key = res_meta["storage_key"]

            # Step H: Download output from MinIO and inspect
            output_bytes = await real_storage.download(
                key=storage_key,
                bucket=real_storage.outputs_bucket,
            )
            assert len(output_bytes) > 0

            # Step I: Verify PDF opens without ANY password and has 3 pages
            reader = pypdf.PdfReader(io.BytesIO(output_bytes))
            assert reader.is_encrypted is False
            assert len(reader.pages) == 3

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
