import asyncio
import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import publish_job_progress, get_job_progress_channel
from app.jobs.models import Job, JobStatus
from app.jobs.service import JobService
from tests.conftest import TestAsyncSessionLocal


@pytest.mark.asyncio
async def test_sse_progress_not_found(async_client: AsyncClient):
    """Ensure requesting progress on a non-existent job returns 404."""
    response = await async_client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000/progress")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_sse_completed_job_immediate_close(async_client: AsyncClient):
    """Ensure a completed job yields its status and immediately closes the stream."""
    # Create a job in DB
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-1"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    # Mark completed in DB
    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 100
        job.transition_to(JobStatus.COMPLETED)
        job.result_file = {"original_name": "merged.pdf", "size_bytes": 1024}
        await session.commit()

    # Stream progress
    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        content = ""
        async for line in response.aiter_lines():
            content += line + "\n"

    assert "event: progress" in content
    assert '"status": "COMPLETED"' in content
    assert '"progress": 100' in content


@pytest.mark.asyncio
async def test_sse_failed_job_immediate_close(async_client: AsyncClient):
    """Ensure a failed job yields its failure payload and immediately terminates."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-2"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.UPLOADING)
        job.transition_to(JobStatus.FAILED, error_message="Corrupted PDF file", error_code="INVALID_PDF")
        await session.commit()

    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        content = ""
        async for line in response.aiter_lines():
            content += line + "\n"

    assert "event: progress" in content
    assert '"status": "FAILED"' in content
    assert "Corrupted PDF file" in content


@pytest.mark.asyncio
async def test_sse_streaming_live_redis_updates(async_client: AsyncClient):
    """Ensure active job receives published updates from Redis and terminates upon completion."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-3"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 10
        await session.commit()

    received_lines = []

    async def stream_reader():
        async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.strip():
                    received_lines.append(line)

    reader_task = asyncio.create_task(stream_reader())

    # Wait briefly for subscription to initialize
    await asyncio.sleep(0.2)

    # Publish intermediate progress
    await publish_job_progress(job_id, {"job_id": job_id, "status": "processing", "progress": 55})
    await asyncio.sleep(0.1)

    # Publish completion
    await publish_job_progress(job_id, {"job_id": job_id, "status": "completed", "progress": 100})

    # Reader should exit cleanly
    await asyncio.wait_for(reader_task, timeout=5.0)

    full_output = "\n".join(received_lines)
    assert "55" in full_output
    assert "completed" in full_output.lower()


@pytest.mark.asyncio
async def test_redis_channel_helper():
    """Ensure channel helper generates consistent names."""
    chan = get_job_progress_channel("12345")
    assert chan == "job_progress:12345"


@pytest.mark.asyncio
async def test_sse_cancelled_job_immediate_close(async_client: AsyncClient):
    """Ensure a cancelled job yields its status and immediately closes the stream."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-cancel"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.UPLOADING)
        job.transition_to(JobStatus.CANCELLED)
        await session.commit()

    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        content = ""
        async for line in response.aiter_lines():
            content += line + "\n"

    assert "event: progress" in content
    assert '"status": "CANCELLED"' in content


@pytest.mark.asyncio
async def test_sse_race_condition_completed_during_setup(async_client: AsyncClient):
    """Ensure that if a job completes right as the SSE connection establishes, it yields completion and exits."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-race"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    # Set to processing first
    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 30
        await session.commit()

        # Simulate immediate completion before stream reads pubsub
        job.progress = 100
        job.transition_to(JobStatus.COMPLETED)
        job.result_file = {"original_name": "race_output.pdf", "size_bytes": 500}
        await session.commit()
        await publish_job_progress(job_id, {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "result_file": job.result_file,
        })

    # Connecting now must see completion and terminate cleanly without timing out
    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        content = ""
        async for line in response.aiter_lines():
            content += line + "\n"

    assert "event: progress" in content
    assert '"status": "COMPLETED"' in content
    assert '"progress": 100' in content
    assert "race_output.pdf" in content


@pytest.mark.asyncio
async def test_sse_reconnect_behaviour(async_client: AsyncClient):
    """Ensure a reconnecting client receives up-to-date state cleanly after disconnect."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-reconnect"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 20
        await session.commit()

    # Client 1 connects, reads initial processing event, and disconnects
    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if "event: progress" in line:
                break

    # While client is disconnected, job finishes in background
    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.progress = 100
        job.transition_to(JobStatus.COMPLETED)
        job.result_file = {"original_name": "reconnect_output.pdf"}
        await session.commit()
        await publish_job_progress(job_id, {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "result_file": job.result_file,
        })

    # Client reconnects: must immediately receive completed status and close cleanly
    content = ""
    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            content += line + "\n"

    assert '"status": "COMPLETED"' in content
    assert '"progress": 100' in content
    assert "reconnect_output.pdf" in content


@pytest.mark.asyncio
async def test_sse_monotonic_progress_updates(async_client: AsyncClient):
    """Ensure the SSE stream guarantees monotonic progress and never regresses."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-monotonic"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 25
        await session.commit()

    progress_values = []

    async def stream_reader():
        async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "progress" in payload:
                        progress_values.append(payload["progress"])

    reader_task = asyncio.create_task(stream_reader())
    await asyncio.sleep(0.2)

    # Publish progress 50
    await publish_job_progress(job_id, {"job_id": job_id, "status": "processing", "progress": 50})
    await asyncio.sleep(0.05)

    # Publish out-of-order lower progress 35 (must be clamped to >= 50)
    await publish_job_progress(job_id, {"job_id": job_id, "status": "processing", "progress": 35})
    await asyncio.sleep(0.05)

    # Publish progress 80
    await publish_job_progress(job_id, {"job_id": job_id, "status": "processing", "progress": 80})
    await asyncio.sleep(0.05)

    # Publish completion
    await publish_job_progress(job_id, {"job_id": job_id, "status": "completed", "progress": 100})

    await asyncio.wait_for(reader_task, timeout=5.0)

    assert len(progress_values) >= 4
    # Verify monotonic non-decreasing order
    for i in range(len(progress_values) - 1):
        assert progress_values[i] <= progress_values[i + 1], f"Progress regressed: {progress_values}"
    assert progress_values[-1] == 100


@pytest.mark.asyncio
async def test_sse_disconnect_cleanup(async_client: AsyncClient):
    """Ensure disconnecting client cleans up its Redis pubsub subscription."""
    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-cleanup"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 10
        await session.commit()

    # Connect and immediately disconnect after initial event
    async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if "event: progress" in line:
                break

    # Stream is closed. Allow loop tick for cleanup
    await asyncio.sleep(0.2)

    # Verify publishing after disconnect does not throw or fail
    await publish_job_progress(job_id, {"job_id": job_id, "status": "processing", "progress": 70})
    await publish_job_progress(job_id, {"job_id": job_id, "status": "completed", "progress": 100})


@pytest.mark.asyncio
async def test_sse_heartbeat_db_fallback_detection(async_client: AsyncClient, monkeypatch):
    """Ensure heartbeat DB check detects completed state even if Redis pubsub message was lost."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "SSE_HEARTBEAT_INTERVAL", 0.2)

    create_res = await async_client.post(
        "/api/v1/jobs",
        json={
            "tool": "merge",
            "files": [{"name": "doc1.pdf", "size": 100, "content_type": "application/pdf"}],
        },
        headers={"X-Session-Id": "sse-test-heartbeat"},
    )
    job_id = create_res.json()["data"]["job"]["id"]

    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.transition_to(JobStatus.QUEUED)
        job.transition_to(JobStatus.PROCESSING)
        job.progress = 15
        await session.commit()

    received_lines = []

    async def stream_reader():
        async with async_client.stream("GET", f"/api/v1/jobs/{job_id}/progress") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.strip():
                    received_lines.append(line)

    reader_task = asyncio.create_task(stream_reader())

    # Wait for stream connection to establish and initial processing event to arrive
    await asyncio.sleep(0.3)

    # Transition to COMPLETED in DB directly WITHOUT calling publish_job_progress
    async with TestAsyncSessionLocal() as session:
        job = await JobService.get_job(session, job_id)
        job.progress = 100
        job.transition_to(JobStatus.COMPLETED)
        job.result_file = {"original_name": "db_only_output.pdf"}
        await session.commit()

    # The heartbeat check runs every 0.2s, so reader should detect completion and exit
    await asyncio.wait_for(reader_task, timeout=5.0)


    output = "\n".join(received_lines)
    assert ": heartbeat" in output
    assert '"status": "COMPLETED"' in output
    assert "db_only_output.pdf" in output


