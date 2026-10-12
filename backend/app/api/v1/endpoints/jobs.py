import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, check_database_health, get_db_session
from app.core.errors import AppException, get_request_id
from app.core.logging import logger
from app.core.redis import check_redis_health, get_job_progress_channel, get_redis_client
from app.core.storage import check_storage_health
from app.jobs.models import JobStatus
from app.jobs.schemas import (
    JobCreateRequest,
    JobDetailData,
    JobStartRequest,
)
from app.jobs.service import JobService

router = APIRouter()


def get_or_create_session_id(x_session_id: str | None = Header(None)) -> str:
    """Extracts or automatically generates an anonymous UUID session ID."""
    if x_session_id and len(x_session_id.strip()) > 0:
        return x_session_id.strip()
    return str(uuid.uuid4())


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create processing job and get presigned upload URLs",
)
async def create_job(
    payload: JobCreateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    session_id: str = Depends(get_or_create_session_id),
) -> dict[str, Any]:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await JobService.create_job(
        session=session,
        payload=payload,
        session_id=session_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {
        "success": True,
        "data": result.model_dump(mode="json"),
        "meta": {
            "request_id": get_request_id(request),
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get(
    "/pipeline-health",
    summary="Check upload and background processing pipeline health",
)
async def get_pipeline_health(request: Request) -> dict[str, Any]:
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    storage_health = await check_storage_health()

    all_connected = (
        db_health.get("status") == "connected"
        and redis_health.get("status") == "connected"
        and storage_health.get("status") == "connected"
    )

    return {
        "success": True,
        "data": {
            "status": "healthy" if all_connected else "degraded",
            "pipeline": {
                "database": db_health,
                "redis": redis_health,
                "storage": storage_health,
            },
        },
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get(
    "/{job_id}",
    summary="Get job status and progress",
)
async def get_job_status(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    job = await JobService.get_job(session=session, job_id=job_id, session_id=session_id)

    detail = JobDetailData(
        id=str(job.id),
        tool=job.tool,
        status=job.status.value,
        progress=job.progress,
        config=job.config,
        input_files=job.input_files,
        result_file=job.result_file,
        error_message=job.error_message,
        error_code=job.error_code,
        error_details=job.error_details,
        started_at=job.started_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
        created_at=job.created_at,
    )

    return {
        "success": True,
        "data": {"job": detail.model_dump(mode="json")},
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get(
    "/{job_id}/progress",
    summary="Stream real-time job progress via Server-Sent Events (SSE)",
)
async def get_job_progress_stream(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
):
    # Verify job existence and session ownership (raises 404 or 403 before starting stream)
    job = await JobService.get_job(session=session, job_id=job_id, session_id=session_id)

    async def event_generator():
        # Fast path check: if job was already in terminal state when requested,
        # yield its final status and terminate stream immediately without Redis.
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.EXPIRED):
            initial_payload = {
                "job_id": str(job.id),
                "status": job.status.value,
                "progress": 100 if job.status == JobStatus.COMPLETED else job.progress,
                "error_message": job.error_message,
                "error_code": job.error_code,
                "result_file": job.result_file,
            }
            yield f"event: progress\ndata: {json.dumps(initial_payload)}\n\n"
            return

        redis_client = get_redis_client()
        pubsub = redis_client.pubsub()
        channel_name = get_job_progress_channel(str(job.id))

        try:
            # 1. Subscribe to Redis pubsub FIRST to ensure no worker messages are missed
            await pubsub.subscribe(channel_name)

            # 2. Re-query latest DB state after subscription is established to eliminate
            # any race window between HTTP arrival and pubsub connection
            async with AsyncSessionLocal() as db_session:
                current_job = await JobService.get_job(db_session, str(job.id), session_id=session_id)
                current_status = current_job.status
                current_progress = current_job.progress
                current_error_msg = current_job.error_message
                current_error_code = current_job.error_code
                current_result_file = current_job.result_file

            initial_payload = {
                "job_id": str(current_job.id),
                "status": current_status.value,
                "progress": 100 if current_status == JobStatus.COMPLETED else current_progress,
                "error_message": current_error_msg,
                "error_code": current_error_code,
                "result_file": current_result_file,
            }
            yield f"event: progress\ndata: {json.dumps(initial_payload)}\n\n"

            # If job finished during setup, exit immediately
            if current_status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.EXPIRED):
                return

            last_heartbeat = asyncio.get_event_loop().time()
            max_duration = 300.0  # Maximum stream lifetime safeguard
            start_time = last_heartbeat
            monotonic_progress = current_progress

            while True:
                if await request.is_disconnected():
                    break

                now = asyncio.get_event_loop().time()
                if now - start_time > max_duration:
                    break

                poll_timeout = min(1.0, max(0.05, settings.SSE_HEARTBEAT_INTERVAL / 2.0))
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=poll_timeout)
                except Exception as e:
                    logger.warning(f"Error reading from pubsub for job {job_id}: {e}")
                    message = None


                now = asyncio.get_event_loop().time()
                if message and message.get("type") == "message":
                    data_str = message.get("data")
                    if data_str:
                        try:
                            parsed = json.loads(data_str)
                            status_val = str(parsed.get("status", "")).lower()

                            # Enforce monotonic progress
                            raw_prog = parsed.get("progress")
                            if raw_prog is not None:
                                if status_val == "completed":
                                    parsed["progress"] = 100
                                elif status_val == "processing":
                                    if raw_prog < monotonic_progress:
                                        parsed["progress"] = monotonic_progress
                                    else:
                                        monotonic_progress = raw_prog

                            yield f"event: progress\ndata: {json.dumps(parsed)}\n\n"

                            if status_val in ("completed", "failed", "cancelled", "expired"):
                                break
                        except Exception:
                            yield f"event: progress\ndata: {data_str}\n\n"

                elif now - last_heartbeat >= settings.SSE_HEARTBEAT_INTERVAL:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now

                    # Fallback check on heartbeat: query DB to ensure terminal states
                    # are detected even if pubsub message was somehow missed
                    try:
                        async with AsyncSessionLocal() as db_session:
                            hb_job = await JobService.get_job(db_session, str(job.id), session_id=session_id)
                            if hb_job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.EXPIRED):
                                hb_payload = {
                                    "job_id": str(hb_job.id),
                                    "status": hb_job.status.value,
                                    "progress": 100 if hb_job.status == JobStatus.COMPLETED else hb_job.progress,
                                    "error_message": hb_job.error_message,
                                    "error_code": hb_job.error_code,
                                    "result_file": hb_job.result_file,
                                }
                                yield f"event: progress\ndata: {json.dumps(hb_payload)}\n\n"
                                break
                    except Exception as e:
                        logger.warning(f"Periodic DB status check error for job {job_id}: {e}")

                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"SSE stream error for job {job_id}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(channel_name)
                if hasattr(pubsub, "aclose"):
                    await pubsub.aclose()
                else:
                    await pubsub.close()
            except Exception as e:
                logger.warning(f"Error cleaning up pubsub for job {job_id}: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@router.post(
    "/{job_id}/files/{file_id}/confirm",
    summary="Confirm that a file was successfully uploaded to Object Storage",
)
async def confirm_file_upload(
    job_id: str,
    file_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    file_meta = await JobService.confirm_file_upload(
        session=session,
        job_id=job_id,
        file_id=file_id,
        session_id=session_id,
    )

    return {
        "success": True,
        "data": {"file": file_meta},
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.put(
    "/{job_id}/files/{file_id}",
    summary="Directly upload a file to the API server",
)
@router.post(
    "/{job_id}/files/{file_id}/upload",
    summary="Directly upload a file to the API server via form-data",
)
async def direct_upload_file(
    job_id: str,
    file_id: str,
    request: Request,
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    if file:
        content = await file.read()
        filename = file.filename
    else:
        content = await request.body()
        filename = None

    if not content:
        raise AppException(
            status_code=422,
            code="VALIDATION_ERROR",
            message="No file content provided",
        )

    file_meta = await JobService.direct_upload_file(
        session=session,
        job_id=job_id,
        file_id=file_id,
        content=content,
        filename=filename,
        session_id=session_id,
    )

    return {
        "success": True,
        "data": {"file": file_meta},
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.post(
    "/{job_id}/start",
    summary="Finalize uploads and start job processing",
)
async def start_job(
    job_id: str,
    request: Request,
    payload: JobStartRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    result = await JobService.start_job(
        session=session,
        job_id=job_id,
        payload=payload,
        session_id=session_id,
    )

    return {
        "success": True,
        "data": {"job": result.model_dump(mode="json")},
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.post(
    "/{job_id}/cancel",
    summary="Cancel a processing job",
)
async def cancel_job(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    job = await JobService.cancel_job(
        session=session,
        job_id=job_id,
        session_id=session_id,
    )

    return {
        "success": True,
        "data": {
            "job": {
                "id": str(job.id),
                "status": job.status.value,
            }
        },
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get(
    "/{job_id}/download",
    summary="Get presigned download URL for completed result file",
)
async def get_download_url(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    session_id: str | None = Header(None, alias="X-Session-Id"),
) -> dict[str, Any]:
    download_info = await JobService.get_job_download(
        session=session,
        job_id=job_id,
        session_id=session_id,
    )

    return {
        "success": True,
        "data": download_info.model_dump(mode="json"),
        "meta": {
            "request_id": get_request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
