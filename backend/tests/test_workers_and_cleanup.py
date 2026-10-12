from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_storage
from app.jobs.models import JobStatus
from app.jobs.schemas import FileInputRequest, JobCreateRequest
from app.jobs.service import JobService
from app.workers.tasks import _async_cleanup_expired_jobs, _async_test_job_pipeline

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.mark.asyncio
async def test_worker_pipeline_execution(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Create job and upload file
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "input.pdf", "size": len(VALID_PDF_BYTES), "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-worker-test"},
    )
    job_id = create_resp.json()["data"]["job"]["id"]
    file_id = create_resp.json()["data"]["uploads"][0]["file_id"]

    await async_client.put(
        f"/api/v1/jobs/{job_id}/files/{file_id}",
        content=VALID_PDF_BYTES,
        headers={"X-Session-Id": "session-worker-test"},
    )

    # 2. Start job -> QUEUED
    await async_client.post(
        f"/api/v1/jobs/{job_id}/start",
        headers={"X-Session-Id": "session-worker-test"},
    )

    # 3. Worker executes task
    res = await _async_test_job_pipeline(job_id)
    assert res["status"] == "COMPLETED"

    # 4. Verify Job updated in PostgreSQL
    job = await JobService.get_job(db_session, job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100
    assert job.result_file is not None
    assert job.result_file["original_name"] == "test_output.pdf"
    assert job.completed_at is not None

    # Verify result file exists in storage
    storage = get_storage()
    assert await storage.exists(job.result_file["storage_key"]) is True

    # 5. Download result URL succeeds
    download_resp = await async_client.get(
        f"/api/v1/jobs/{job_id}/download",
        headers={"X-Session-Id": "session-worker-test"},
    )
    assert download_resp.status_code == 200
    assert "download_url" in download_resp.json()["data"]


@pytest.mark.asyncio
async def test_worker_failure_handling(db_session: AsyncSession):
    # Create job directly in QUEUED state with an invalid state or non-existent file
    job_resp = await JobService.create_job(
        session=db_session,
        payload=JobCreateRequest(
            tool="merge",
            files=[FileInputRequest(name="test.pdf", size=100)],
            config={},
        ),
        session_id="session-fail-test",
    )
    job_id = job_resp.job.id

    # Force a failure during worker execution
    job = await JobService.get_job(db_session, job_id)
    job.transition_to(JobStatus.QUEUED)
    await db_session.commit()

    # Worker processing with mock exception
    storage = get_storage()
    original_upload = storage.upload

    async def broken_upload(*args, **kwargs):
        raise RuntimeError("Simulated Object Storage Write Failure")

    storage.upload = broken_upload
    try:
        with pytest.raises(RuntimeError):
            await _async_test_job_pipeline(job_id)

        # Verify job is marked as FAILED in PostgreSQL
        await db_session.refresh(job)
        assert job.status == JobStatus.FAILED
        assert "Simulated Object Storage Write Failure" in (job.error_message or "")
        assert job.error_code == "PROCESSING_ERROR"
    finally:
        storage.upload = original_upload


@pytest.mark.asyncio
async def test_job_cleanup_and_expiration(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Create and complete a job
    create_resp = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "expire.pdf", "size": len(VALID_PDF_BYTES), "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "session-cleanup-test"},
    )
    job_id = create_resp.json()["data"]["job"]["id"]
    file_id = create_resp.json()["data"]["uploads"][0]["file_id"]

    await async_client.put(
        f"/api/v1/jobs/{job_id}/files/{file_id}",
        content=VALID_PDF_BYTES,
        headers={"X-Session-Id": "session-cleanup-test"},
    )
    await async_client.post(f"/api/v1/jobs/{job_id}/start", headers={"X-Session-Id": "session-cleanup-test"})
    await _async_test_job_pipeline(job_id)

    job = await JobService.get_job(db_session, job_id)
    input_key = job.input_files[0]["storage_key"]
    output_key = job.result_file["storage_key"]

    storage = get_storage()
    assert await storage.exists(input_key) is True
    assert await storage.exists(output_key) is True

    # 2. Age the job to simulate TTL expiration
    job.expires_at = datetime.now(UTC) - timedelta(minutes=10)
    await db_session.commit()

    # 3. Run cleanup task
    cleaned_count = await _async_cleanup_expired_jobs()
    assert cleaned_count >= 1

    # 4. Verify storage files deleted
    assert await storage.exists(input_key) is False
    assert await storage.exists(output_key) is False

    # 5. Verify status is EXPIRED
    await db_session.refresh(job)
    assert job.status == JobStatus.EXPIRED

    # 6. Verify expired file cannot be downloaded (410 FILE_EXPIRED)
    down_resp = await async_client.get(
        f"/api/v1/jobs/{job_id}/download",
        headers={"X-Session-Id": "session-cleanup-test"},
    )
    assert down_resp.status_code == 410
    assert down_resp.json()["error"]["code"] == "FILE_EXPIRED"

    # 7. Safe to retry: Running cleanup again on the already cleaned job is safe and does not crash
    re_clean_count = await _async_cleanup_expired_jobs()
    assert re_clean_count == 0
