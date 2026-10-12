import asyncio
import io
import time
import uuid

import pikepdf
import pypdf
import pytest
from httpx import ASGITransport, AsyncClient

import app.core.database as db_core
from app.core.storage import S3StorageBackend, get_storage, set_storage_backend
from app.jobs.models import JobStatus
from app.jobs.service import JobService
from app.main import app
from app.workers.tasks import process_job_task
from tests.test_celery_redis_integration import is_minio_available, is_redis_available


def create_damaged_startxref_pdf(num_pages: int = 2) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    data = buf.getvalue()

    idx = data.rfind(b"startxref\n")
    assert idx != -1
    line_end = data.find(b"\n", idx + 10)
    return data[:idx + 10] + b"8888888\n" + data[line_end + 1:]


@pytest.mark.skipif(
    not (is_redis_available() and is_minio_available()),
    reason="Live Redis or MinIO not available for end-to-end integration test",
)
@pytest.mark.asyncio
async def test_repair_pdf_real_worker_execution(monkeypatch):
    """
    End-to-end integration test for Repair PDF with live Celery worker, Redis, MinIO, and PostgreSQL.
    Verifies:
    1. A damaged PDF upload triggers a background repair job.
    2. Celery worker executes RepairPDFHandler.
    3. Reconstructed output PDF is written to MinIO and marked COMPLETED in PostgreSQL.
    4. Result file can be downloaded and opened as a valid, recovered PDF.
    """
    real_storage = S3StorageBackend()
    set_storage_backend(real_storage)

    damaged_pdf = create_damaged_startxref_pdf(num_pages=2)
    session_id = f"test-repair-e2e-{uuid.uuid4().hex[:8]}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create Job
        create_resp = await client.post(
            "/api/v1/jobs",
            json={
                "tool": "repair",
                "files": [
                    {
                        "name": "damaged_doc.pdf",
                        "size": len(damaged_pdf),
                        "content_type": "application/pdf",
                    }
                ],
                "config": {"output_filename": "restored.pdf"},
            },
            headers={"X-Session-Id": session_id},
        )
        assert create_resp.status_code == 201
        create_data = create_resp.json()["data"]
        job_id = create_data["job"]["id"]
        uploads = create_data["uploads"]
        assert len(uploads) == 1
        file_id = uploads[0]["file_id"]

        # Step 2: Upload damaged PDF via API endpoint
        up_resp = await client.put(
            f"/api/v1/jobs/{job_id}/files/{file_id}",
            content=damaged_pdf,
            headers={"X-Session-Id": session_id},
        )
        assert up_resp.status_code == 200

        # Step 3: Start job
        start_resp = await client.post(
            f"/api/v1/jobs/{job_id}/start",
            json={"config": {"output_filename": "restored.pdf"}},
            headers={"X-Session-Id": session_id},
        )
        assert start_resp.status_code == 200

        # Step 4: Queue task to Celery on Redis
        process_job_task.apply_async(args=[job_id])

        # Step 5: Poll PostgreSQL for COMPLETED status
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

        assert completed is True, f"Repair job did not complete within timeout. Last status: {last_status}"

        # Step 6: Verify job details and repair metadata
        async with db_core.AsyncSessionLocal() as session:
            job = await JobService.get_job(session, job_id)
            assert job.progress == 100
            res = job.result_file
            assert res is not None
            assert res["original_name"] == "restored.pdf"
            assert res["repaired"] is True
            assert res["repair_action"] == "XREF_RECONSTRUCTED"
            assert res["page_count"] == 2

            # Step 7: Verify output in storage can be opened and read as a valid PDF
            storage = get_storage()
            output_bytes = await storage.download(res["storage_key"])
            with pikepdf.Pdf.open(io.BytesIO(output_bytes), attempt_recovery=False) as verified_pdf:
                assert len(verified_pdf.pages) == 2
