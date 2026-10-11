import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

import app.core.database as db_core
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.core.storage import get_storage
from app.core.redis import publish_job_progress
from app.jobs.models import Job, JobStatus
from app.jobs.service import JobService, generate_output_storage_key
from app.tools.registry import get_tool_handler
from app.tools.base import ProcessingContext
from app.workers.celery_app import celery_app

# Dedicated worker engine with NullPool to prevent event-loop-closed errors across Celery task executions
worker_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)
WorkerAsyncSessionLocal = async_sessionmaker(
    bind=worker_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_worker_session_maker() -> async_sessionmaker[AsyncSession]:
    """Returns test-isolated sessionmaker if patched in tests, else WorkerAsyncSessionLocal with NullPool."""
    if hasattr(db_core, "AsyncSessionLocal") and "test" in str(getattr(db_core, "engine", "")).lower():
        return db_core.AsyncSessionLocal
    return WorkerAsyncSessionLocal


async def _async_process_job(job_id: str) -> Dict[str, Any]:
    """Asynchronous background pipeline for processing a PDF tool job."""
    session_factory = get_worker_session_maker()
    async with session_factory() as session:
        job = await JobService.get_job(session, job_id)
        storage = get_storage()

        # Check expiration or cancelled before starting
        if job.is_expired():
            logger.warning(f"Job {job_id} is expired. Aborting processing.")
            return {"job_id": job_id, "status": job.status.value}
        if job.status == JobStatus.CANCELLED:
            logger.warning(f"Job {job_id} was cancelled. Aborting processing.")
            return {"job_id": job_id, "status": job.status.value}

        try:
            # 1. Transition to PROCESSING
            job.transition_to(JobStatus.PROCESSING)
            job.progress = 10
            await session.commit()
            await session.refresh(job)
            await publish_job_progress(job_id, {
                "job_id": job_id,
                "status": "processing",
                "progress": 10,
            })

            # 2. Get tool handler
            handler = get_tool_handler(job.tool)

            # 3. Security Guard: Ensure all input files completed security validation
            for file_meta in job.input_files or []:
                if not file_meta.get("security_scanned"):
                    raise AppException(
                        status_code=400,
                        code="UNSCANNED_FILE_REJECTED",
                        message=f"File {file_meta.get('original_name', 'input')} has not passed security verification.",
                    )

            # 4. Create isolated temporary directory
            with tempfile.TemporaryDirectory(prefix=f"docforge_job_{job_id}_", ignore_cleanup_errors=True) as temp_dir:
                # 5. Download input files to temp directory
                downloaded_files: List[Dict[str, Any]] = []
                for file_meta in job.input_files or []:
                    storage_key = file_meta.get("storage_key")
                    fid = file_meta.get("id")
                    if not storage_key or not await storage.exists(storage_key):
                        raise AppException(
                            status_code=404,
                            code="FILE_NOT_FOUND",
                            message=f"Storage object not found for file {file_meta.get('original_name', fid)}",
                        )
                    orig_name = file_meta.get("original_name", "")
                    _, file_ext = os.path.splitext(orig_name)
                    if not file_ext:
                        file_ext = ".jpg" if job.tool.lower() in ("jpg_to_pdf", "jpg-to-pdf") else ".pdf"
                    local_path = os.path.join(temp_dir, f"{fid}{file_ext}")
                    file_bytes = await storage.download(storage_key)
                    with open(local_path, "wb") as f_local:
                        f_local.write(file_bytes)

                    downloaded_files.append({
                        **file_meta,
                        "local_path": local_path,
                    })

                # Progress callback
                async def progress_callback(percent: int) -> None:
                    job.progress = min(percent, 95)
                    await session.commit()
                    await publish_job_progress(job_id, {
                        "job_id": job_id,
                        "status": "processing",
                        "progress": job.progress,
                    })

                # Check for ephemeral password in Redis
                worker_config = dict(job.config or {})
                try:
                    import redis.asyncio as aioredis
                    worker_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                    try:
                        ephemeral_pw = await worker_redis.get(f"ephemeral_job_password:{job_id}")
                        if ephemeral_pw:
                            worker_config["password"] = ephemeral_pw
                            # Immediately delete from Redis so it is not retained
                            await worker_redis.delete(f"ephemeral_job_password:{job_id}")
                    finally:
                        await worker_redis.aclose()
                except Exception as e:
                    logger.warning(f"Ephemeral password lookup error: {e}")

                context = ProcessingContext(
                    job_id=str(job.id),
                    input_files=downloaded_files,
                    config=worker_config,
                    temp_dir=temp_dir,
                    progress_callback=progress_callback,
                )

                # 5. Process tool logic
                result = await handler.process(context)

                # Explicitly wipe sensitive in-memory references
                if "password" in worker_config:
                    worker_config["password"] = None
                if "password" in context.config:
                    context.config["password"] = None

                # 6. Upload output file to storage
                output_path = result["output_path"]
                with open(output_path, "rb") as f_out:
                    output_bytes = f_out.read()

                output_file_id = str(uuid.uuid4())
                filename = result["filename"]
                is_zip = filename.lower().endswith(".zip")
                ext = "zip" if is_zip else "pdf"
                content_type = result.get("content_type", "application/zip" if is_zip else "application/pdf")
                output_storage_key = generate_output_storage_key(str(job.id), output_file_id, extension=ext)

                await storage.upload(
                    key=output_storage_key,
                    data=output_bytes,
                    content_type=content_type,
                    bucket=storage.outputs_bucket if hasattr(storage, "outputs_bucket") else None,
                )

                # 7. Finalize job in PostgreSQL (passwords are strictly never stored)
                job.result_file = {
                    "id": output_file_id,
                    "original_name": filename,
                    "size_bytes": result["size_bytes"],
                    "page_count": result.get("page_count"),
                    "file_count": result.get("file_count"),
                    "original_size_bytes": result.get("original_size_bytes"),
                    "savings_bytes": result.get("savings_bytes"),
                    "savings_percentage": result.get("savings_percentage"),
                    "is_already_optimal": result.get("is_already_optimal"),
                    "compression_level": result.get("compression_level"),
                    "rotation_angle": result.get("rotation_angle"),
                    "rotated_pages_count": result.get("rotated_pages_count"),
                    "watermark_text": result.get("watermark_text"),
                    "watermarked_pages_count": result.get("watermarked_pages_count"),
                    "numbered_pages_count": result.get("numbered_pages_count"),
                    "numbering_format": result.get("numbering_format"),
                    "position": result.get("position"),
                    "is_encrypted": result.get("is_encrypted", True if job.tool == "protect" else False),
                    "encryption_algorithm": result.get("encryption_algorithm"),
                    "repaired": result.get("repaired"),
                    "repair_action": result.get("repair_action"),
                    "status_detail": result.get("status_detail"),
                    "sha256": result.get("sha256"),
                    "storage_key": output_storage_key,
                    "content_type": content_type,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                job.progress = 100
                job.transition_to(JobStatus.COMPLETED)
                await session.commit()
                await session.refresh(job)

                await publish_job_progress(job_id, {
                    "job_id": job_id,
                    "status": "completed",
                    "progress": 100,
                    "result_file": job.result_file,
                })

                logger.info(f"Job {job_id} ({job.tool}) completed successfully.")
                return {"job_id": job_id, "status": "COMPLETED"}

        except Exception as e:
            logger.error(f"Job {job_id} processing failed: {e}")
            error_msg = e.message if isinstance(e, AppException) else str(e)
            error_code = e.code if isinstance(e, AppException) else "PROCESSING_ERROR"
            error_details = {"exception": type(e).__name__}

            job.transition_to(
                JobStatus.FAILED,
                error_message=error_msg,
                error_code=error_code,
                error_details=error_details,
            )
            await session.commit()

            await publish_job_progress(job_id, {
                "job_id": job_id,
                "status": "failed",
                "progress": job.progress,
                "error_message": error_msg,
                "error_code": error_code,
            })
            raise


@celery_app.task(name="app.workers.tasks.process_job_task", bind=True, max_retries=2)
def process_job_task(self, job_id: str) -> Dict[str, Any]:
    """Celery task entrypoint for all registered tool processing jobs."""
    try:
        return asyncio.run(_async_process_job(job_id))
    except Exception as exc:
        logger.error(f"Worker task error for job {job_id}: {exc}")
        raise exc




async def _async_test_job_pipeline(job_id: str) -> Dict[str, Any]:
    """Async execution for the basic test processing job."""
    session_factory = get_worker_session_maker()
    async with session_factory() as session:
        job = await JobService.get_job(session, job_id)
        storage = get_storage()

        try:
            # Step 1: Transition to PROCESSING
            job.transition_to(JobStatus.PROCESSING)
            job.progress = 20
            await session.commit()
            await session.refresh(job)

            # Step 2: Simulate intermediate progress
            await asyncio.sleep(0.1)
            job.progress = 60
            await session.commit()
            await session.refresh(job)

            # Step 3: Create simulated output file in storage
            output_file_id = str(uuid.uuid4())
            output_storage_key = generate_output_storage_key(str(job.id), output_file_id)
            dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"

            await storage.upload(
                key=output_storage_key,
                data=dummy_pdf_content,
                content_type="application/pdf",
                bucket=storage.outputs_bucket if hasattr(storage, "outputs_bucket") else None,
            )

            job.result_file = {
                "id": output_file_id,
                "original_name": "test_output.pdf",
                "size_bytes": len(dummy_pdf_content),
                "content_type": "application/pdf",
                "storage_key": output_storage_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            job.progress = 100

            # Step 4: Transition to COMPLETED
            job.transition_to(JobStatus.COMPLETED)
            await session.commit()
            await session.refresh(job)

            logger.info(f"Test job {job_id} successfully completed.")
            return {"job_id": job_id, "status": "COMPLETED"}

        except Exception as e:
            logger.error(f"Test job {job_id} processing failed: {e}")
            job.transition_to(
                JobStatus.FAILED,
                error_message=str(e),
                error_code="PROCESSING_ERROR",
                error_details={"exception": type(e).__name__},
            )
            await session.commit()
            raise


@celery_app.task(name="app.workers.tasks.test_job_task", bind=True, max_retries=2)
def test_job_task(self, job_id: str) -> Dict[str, Any]:
    """Celery task entrypoint for test processing jobs."""
    try:
        return asyncio.run(_async_test_job_pipeline(job_id))
    except Exception as exc:
        logger.error(f"Worker task error for job {job_id}: {exc}")
        raise exc


async def _async_cleanup_expired_jobs() -> int:
    session_factory = get_worker_session_maker()
    async with session_factory() as session:
        return await JobService.cleanup_expired_jobs(session)


@celery_app.task(name="app.workers.tasks.cleanup_expired_jobs_task")
def cleanup_expired_jobs_task() -> int:
    """Celery Beat task entrypoint for cleaning up expired jobs and storage objects."""
    cleaned = asyncio.run(_async_cleanup_expired_jobs())
    logger.info(f"Cleanup expired jobs completed. Cleaned {cleaned} jobs.")
    return cleaned
