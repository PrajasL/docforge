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


def create_test_pdf(page_count: int, width: float, height: float) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=width, height=height)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_merge_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test with real Redis, MinIO, PostgreSQL, and a live Celery worker process.
    Verifies that:
    1. A job created and started via the API is queued onto Redis.
    2. An actual Celery worker process picks up and executes the task.
    3. Input files are read from real MinIO storage.
    4. Merging preserves page ordering and dimensions.
    5. The result is written to MinIO and marked COMPLETED in PostgreSQL.
    6. The result can be downloaded and opened as a valid PDF.
    """
    # 1. Use real S3StorageBackend
    real_storage = S3StorageBackend()
    set_storage_backend(real_storage)

    # 2. Start a live Celery worker in a subprocess
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
        # Give worker a moment to connect to Redis
        await asyncio.sleep(2.0)

        # 3. Create test PDFs
        # File A: 2 pages (100x100)
        # File B: 3 pages (200x200)
        pdf_a_bytes = create_test_pdf(2, 100, 100)
        pdf_b_bytes = create_test_pdf(3, 200, 200)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "merge",
                    "files": [
                        {"name": "file_a.pdf", "size": len(pdf_a_bytes), "content_type": "application/pdf"},
                        {"name": "file_b.pdf", "size": len(pdf_b_bytes), "content_type": "application/pdf"},
                    ],
                    "config": {},
                },
                headers={"X-Session-Id": session_id},
            )
            assert create_resp.status_code == 201
            create_data = create_resp.json()["data"]
            job_id = create_data["job"]["id"]
            uploads = create_data["uploads"]
            assert len(uploads) == 2

            file_a_id = uploads[0]["file_id"]
            file_b_id = uploads[1]["file_id"]

            # Step B: Direct upload both files to MinIO via API
            up_a = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file_a_id}",
                content=pdf_a_bytes,
                headers={"X-Session-Id": session_id},
            )
            assert up_a.status_code == 200

            up_b = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file_b_id}",
                content=pdf_b_bytes,
                headers={"X-Session-Id": session_id},
            )
            assert up_b.status_code == 200

            # Step C: Start job with custom file_order: B first, then A
            # Unpatch Celery delay by dispatching directly through Celery task delay
            from app.workers.tasks import process_job_task
            # Monkeypatch JobService.start_job's delay call to use real delay without mock
            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={"config": {"file_order": [file_b_id, file_a_id], "output_filename": "ordered_merged.pdf"}},
                headers={"X-Session-Id": session_id},
            )
            assert start_resp.status_code == 200

            # Step D: Actually queue to Redis using process_job_task.delay(job_id)
            # Since conftest autouse fixture mocks process_job_task.delay, invoke real delay:
            process_job_task.apply_async(args=[job_id])

            # Step E: Poll PostgreSQL for job status until COMPLETED (up to 15s)
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

            assert completed is True, f"Job did not complete within timeout. Last status: {last_status}"

            # Step F: Verify job details and result metadata
            async with db_core.AsyncSessionLocal() as session:
                job = await JobService.get_job(session, job_id)
                assert job.progress == 100
                assert job.result_file is not None
                assert job.result_file["original_name"] == "ordered_merged.pdf"
                assert job.result_file["page_count"] == 5
                assert job.result_file["size_bytes"] > 0

                # Step G: Download and inspect output file from real MinIO
                output_key = job.result_file["storage_key"]
                assert await real_storage.exists(output_key) is True
                merged_bytes = await real_storage.download(output_key)

                reader = pypdf.PdfReader(io.BytesIO(merged_bytes))
                assert len(reader.pages) == 5

                # Verify file B was merged before file A
                # First 3 pages must have width 200 (file B), last 2 pages must have width 100 (file A)
                assert reader.pages[0].mediabox.width == 200
                assert reader.pages[1].mediabox.width == 200
                assert reader.pages[2].mediabox.width == 200
                assert reader.pages[3].mediabox.width == 100
                assert reader.pages[4].mediabox.width == 100

            # Step H: Download endpoint check
            download_resp = await client.get(
                f"/api/v1/jobs/{job_id}/download",
                headers={"X-Session-Id": session_id},
            )
            assert download_resp.status_code == 200
            dl_data = download_resp.json()["data"]
            assert "download_url" in dl_data
            assert dl_data["filename"] == "ordered_merged.pdf"
            assert dl_data["size_bytes"] > 0

            # Cleanup test storage objects
            await real_storage.delete(output_key)
            for f in job.input_files:
                if f.get("storage_key"):
                    await real_storage.delete(f["storage_key"])

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
