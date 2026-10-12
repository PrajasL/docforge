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
from app.workers.tasks import process_job_task
from tests.test_celery_redis_integration import is_minio_available, is_redis_available


def create_test_pdf(page_count: int = 5) -> bytes:
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
async def test_extract_pages_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Extract Pages with real Redis, MinIO, PostgreSQL, and a live Celery worker.
    Verifies that:
    1. An Extract Pages job created and started via API is processed by the background worker.
    2. Input file is downloaded from MinIO.
    3. Selected pages (e.g. '4, 2, 1') are extracted in exact custom order.
    4. Output is uploaded to MinIO as a single PDF.
    5. Downloaded output contains exactly 3 pages with matching dimensions.
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

        pdf_bytes = create_test_pdf(5)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = f"test-extract-e2e-{uuid.uuid4()}"

            # Step A: Create job
            create_resp = await client.post(
                "/api/v1/jobs",
                json={
                    "tool": "extract_pages",
                    "files": [
                        {"name": "annual_report.pdf", "size": len(pdf_bytes), "content_type": "application/pdf"}
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

            # Step C: Start job with custom extract ranges
            start_resp = await client.post(
                f"/api/v1/jobs/{job_id}/start",
                json={
                    "config": {
                        "pages": "4, 2, 1",
                        "output_filename": "extracted_report_pages.pdf",
                    }
                },
                headers={"X-Session-Id": session_id},
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

            if not completed:
                worker_proc.terminate()
                stdout, stderr = worker_proc.communicate(timeout=3)
                print("WORKER STDOUT:\n", stdout.decode("utf-8", errors="replace"))
                print("WORKER STDERR:\n", stderr.decode("utf-8", errors="replace"))

            assert completed, f"Job timed out before completion. Final status was {last_status}"

            # Step F: Validate result file metadata
            async with db_core.AsyncSessionLocal() as session:
                final_job = await JobService.get_job(session, job_id)
                res_meta = final_job.result_file
                assert res_meta is not None
                assert res_meta["original_name"] == "extracted_report_pages.pdf"
                assert res_meta["page_count"] == 3
                assert res_meta["content_type"] == "application/pdf"
                storage_key = res_meta["storage_key"]

            # Step G: Download output from MinIO and inspect
            output_bytes = await real_storage.download(
                key=storage_key,
                bucket=real_storage.outputs_bucket,
            )
            assert len(output_bytes) > 0

            # Step H: Verify extracted PDF pages and dimensions
            reader = pypdf.PdfReader(io.BytesIO(output_bytes))
            assert len(reader.pages) == 3
            # Page 1 (original page 4: width 350, height 450)
            assert float(reader.pages[0].mediabox.width) == 350.0
            assert float(reader.pages[0].mediabox.height) == 450.0
            # Page 2 (original page 2: width 250, height 350)
            assert float(reader.pages[1].mediabox.width) == 250.0
            assert float(reader.pages[1].mediabox.height) == 350.0
            # Page 3 (original page 1: width 200, height 300)
            assert float(reader.pages[2].mediabox.width) == 200.0
            assert float(reader.pages[2].mediabox.height) == 300.0

    finally:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
