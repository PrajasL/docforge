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

import app.core.database as db_core
from app.core.storage import S3StorageBackend, set_storage_backend
from app.jobs.models import JobStatus
from app.jobs.service import JobService
from app.main import app
from tests.test_celery_redis_integration import is_minio_available, is_redis_available


def create_test_pdf(page_count: int, start_width: float = 100) -> bytes:
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        writer.add_blank_page(width=start_width + i * 10, height=start_width + i * 10)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_split_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Split PDF with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. A Split PDF job created and started via the API is queued onto Redis.
    2. An actual Celery worker process picks up and executes the task.
    3. Input files are read from real MinIO storage.
    4. Splitting creates valid individual PDFs inside a ZIP archive.
    5. The result ZIP is uploaded to MinIO and marked COMPLETED in PostgreSQL.
    6. The result can be downloaded via presigned URL and unzipped to inspect valid PDFs with exact page ranges.
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

        # 3. Create a 4-page test PDF (pages with widths 100, 110, 120, 130)
        pdf_bytes = create_test_pdf(4, start_width=100)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-split-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "split",
                    "files": [
                        {"name": "multi_page.pdf", "size": len(pdf_bytes), "content_type": "application/pdf"}
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

            # Step B: Direct upload file to MinIO via API
            up_resp = await client.put(
                f"/api/v1/jobs/{job_id}/files/{file_id}",
                content=pdf_bytes,
                headers={"X-Session-Id": session_id},
            )
            assert up_resp.status_code == 200

            # Step C: Start job with custom ranges: "1-2, 3-4"
            from app.workers.tasks import process_job_task

            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "mode": "ranges",
                        "ranges": "1-2, 3-4",
                        "output_filename": "real_split_result.zip",
                    }
                },
                headers={"X-Session-Id": session_id},
            )
            assert start_resp.status_code == 200

            # Step D: Actually queue to Redis using process_job_task
            process_job_task.apply_async(args=[job_id])

            # Step E: Poll PostgreSQL for job status until COMPLETED
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

            assert completed is True, f"Split job did not complete within timeout. Last status: {last_status}"

            # Step F: Verify job details and result metadata
            async with db_core.AsyncSessionLocal() as session:
                job = await JobService.get_job(session, job_id)
                assert job.progress == 100
                assert job.result_file is not None
                assert job.result_file["original_name"] == "real_split_result.zip"
                assert job.result_file["content_type"] == "application/zip"
                assert job.result_file["file_count"] == 2
                assert job.result_file["size_bytes"] > 0

                # Step G: Download and inspect output ZIP from real MinIO
                output_key = job.result_file["storage_key"]
                assert await real_storage.exists(output_key) is True
                zip_bytes = await real_storage.download(output_key)

                # Step H: Verify ZIP contents
                with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                    namelist = zf.namelist()
                    assert "range_1-2.pdf" in namelist
                    assert "range_3-4.pdf" in namelist

                    # Verify range_1-2.pdf has 2 pages
                    r1 = pypdf.PdfReader(io.BytesIO(zf.read("range_1-2.pdf")))
                    assert len(r1.pages) == 2
                    assert r1.pages[0].mediabox.width == 100
                    assert r1.pages[1].mediabox.width == 110

                    # Verify range_3-4.pdf has 2 pages
                    r2 = pypdf.PdfReader(io.BytesIO(zf.read("range_3-4.pdf")))
                    assert len(r2.pages) == 2
                    assert r2.pages[0].mediabox.width == 120
                    assert r2.pages[1].mediabox.width == 130

            # Step I: Verify download API endpoint
            download_resp = await client.get(
                f"/api/v1/jobs/{job_id}/download",
                headers={"X-Session-Id": session_id},
            )
            assert download_resp.status_code == 200
            dl_data = download_resp.json()["data"]
            assert "download_url" in dl_data
            assert dl_data["filename"] == "real_split_result.zip"
            assert dl_data["content_type"] == "application/zip"

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
