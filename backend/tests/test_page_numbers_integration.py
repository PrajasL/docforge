import asyncio
import io
import os
import subprocess
import sys
import time
import uuid

import pypdf
import pytest
from httpx import ASGITransport, AsyncClient

import app.core.database as db_core
from app.core.storage import S3StorageBackend, set_storage_backend
from app.jobs.models import JobStatus
from app.jobs.service import JobService
from app.main import app
from tests.test_celery_redis_integration import is_minio_available, is_redis_available


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
async def test_page_numbers_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Add Page Numbers PDF with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. An Add Page Numbers job created and started via the API is queued onto Redis.
    2. An actual Celery worker process picks up and executes the task.
    3. Input file is read from real MinIO storage.
    4. Page numbers are stamped onto selected pages with configured format and position.
    5. Result PDF is uploaded to MinIO and marked COMPLETED in PostgreSQL.
    6. Result metadata accurately records numbered pages count and formatting.
    7. The downloaded PDF opens cleanly and contains the stamped page numbers.
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
            session_id = f"test-page-numbers-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "page_numbers",
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

            # Step C: Start job with Page Numbers config
            from app.workers.tasks import process_job_task

            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "position": "bottom_center",
                        "format": "page_n_of_total",
                        "start_page": 2,
                        "start_number": 1,
                        "font_size": 12,
                        "color": "#111827",
                        "output_filename": "numbered_doc.pdf",
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

            # Step F: Validate result file metadata in database
            async with db_core.AsyncSessionLocal() as session:
                final_job = await JobService.get_job(session, job_id)
                res_meta = final_job.result_file
                assert res_meta is not None
                assert res_meta["original_name"] == "numbered_doc.pdf"
                assert res_meta["page_count"] == 3
                assert res_meta["numbered_pages_count"] == 2
                assert res_meta["numbering_format"] == "page_n_of_total"
                assert res_meta["position"] == "bottom_center"
                storage_key = res_meta["storage_key"]

            # Step G: Download and inspect output PDF from MinIO
            output_bytes = await real_storage.download(
                key=storage_key,
                bucket=real_storage.outputs_bucket,
            )
            assert len(output_bytes) > 0

            # Step H: Validate page numbers presence on pages
            reader = pypdf.PdfReader(io.BytesIO(output_bytes))
            assert len(reader.pages) == 3
            # Page 1 (index 0) was before start_page 2, so no number
            assert "Page" not in reader.pages[0].extract_text()
            # Page 2 (index 1) has Page 1 of 2
            assert "Page 1 of 2" in reader.pages[1].extract_text()
            # Page 3 (index 2) has Page 2 of 2
            assert "Page 2 of 2" in reader.pages[2].extract_text()

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
