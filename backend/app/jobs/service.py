import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.core.storage import StorageBackend, get_storage
from app.files.validator import (
    sanitize_filename,
    scan_file_content,
    validate_file_extension,
    validate_jpg_extension,
    validate_jpg_file,
    validate_jpg_magic_bytes,
    validate_pdf_file,
    validate_pdf_magic_bytes,
)
from app.jobs.models import Job, JobStatus
from app.jobs.schemas import (
    JobCreateData,
    JobCreateRequest,
    JobDownloadData,
    JobStartData,
    JobStartRequest,
    JobSummary,
    PresignedUploadItem,
)


def generate_input_storage_key(job_id: str, file_id: str, extension: str = "pdf") -> str:
    """Generates date-partitioned storage key for input files: inputs/YYYY/MM/DD/{job_id}/{file_id}.{ext}"""
    now = datetime.now(UTC)
    ext = extension.lstrip(".")
    return f"inputs/{now.year}/{now.month:02d}/{now.day:02d}/{job_id}/{file_id}.{ext}"


def generate_output_storage_key(job_id: str, file_id: str, extension: str = "pdf") -> str:
    """Generates date-partitioned storage key for output files: outputs/YYYY/MM/DD/{job_id}/{file_id}.{ext}"""
    now = datetime.now(UTC)
    ext = extension.lstrip(".")
    return f"outputs/{now.year}/{now.month:02d}/{now.day:02d}/{job_id}/{file_id}.{ext}"


class JobService:
    @staticmethod
    async def create_job(
        session: AsyncSession,
        payload: JobCreateRequest,
        session_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        storage: StorageBackend | None = None,
    ) -> JobCreateData:
        storage_client = storage or get_storage()

        is_pdf_to_jpg = payload.tool.lower() in ("pdf_to_jpg", "pdf-to-jpg")
        is_jpg_to_pdf = payload.tool.lower() in ("jpg_to_pdf", "jpg-to-pdf")

        # Enforce configurable file count limits
        max_files_allowed = settings.JPG_TO_PDF_MAX_FILES if is_jpg_to_pdf else settings.MAX_FILES_PER_JOB
        if len(payload.files) > max_files_allowed:
            raise AppException(
                status_code=400,
                code="TOO_MANY_FILES",
                message=f"Exceeded maximum files limit of {max_files_allowed}",
            )

        if is_jpg_to_pdf:
            tool_max_mb = settings.JPG_TO_PDF_MAX_FILE_SIZE_MB
        elif is_pdf_to_jpg:
            tool_max_mb = settings.PDF_TO_JPG_MAX_FILE_SIZE_MB
        else:
            tool_max_mb = settings.MAX_FILE_SIZE_MB
        max_size_bytes = tool_max_mb * 1024 * 1024
        total_size = 0

        # Validate each declared file
        for f in payload.files:
            if f.size <= 0:
                raise AppException(
                    status_code=422,
                    code="VALIDATION_ERROR",
                    message=f"File '{f.name}' has invalid size of 0 bytes",
                )
            if is_jpg_to_pdf:
                if not validate_jpg_extension(f.name):
                    raise AppException(
                        status_code=415,
                        code="INVALID_CONTENT_TYPE",
                        message=f"File '{f.name}' does not have a valid .jpg or .jpeg extension",
                    )
            else:
                if not validate_file_extension(f.name):
                    raise AppException(
                        status_code=415,
                        code="INVALID_CONTENT_TYPE",
                        message=f"File '{f.name}' does not have a .pdf extension",
                    )
            if f.size > max_size_bytes:
                raise AppException(
                    status_code=413,
                    code="FILE_TOO_LARGE",
                    message=f"File '{f.name}' exceeds maximum size of {tool_max_mb} MB",
                )
            total_size += f.size

        # Validate cumulative aggregate upload limit
        max_aggregate_bytes = settings.MAX_AGGREGATE_JOB_SIZE_MB * 1024 * 1024
        if total_size > max_aggregate_bytes:
            raise AppException(
                status_code=413,
                code="PAYLOAD_TOO_LARGE",
                message=f"Total upload size of {total_size // (1024 * 1024)} MB exceeds maximum allowed aggregate size of {settings.MAX_AGGREGATE_JOB_SIZE_MB} MB",
            )

        # Job TTL
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=settings.DEFAULT_JOB_TTL_SECONDS)
        job_id = uuid.uuid4()

        input_files_meta: list[dict[str, Any]] = []
        upload_items: list[PresignedUploadItem] = []

        for f in payload.files:
            file_id = str(uuid.uuid4())
            sanitized_name = sanitize_filename(f.name, default_ext=".jpg" if is_jpg_to_pdf else ".pdf")
            file_ext = "jpg" if is_jpg_to_pdf else "pdf"
            content_type = "image/jpeg" if is_jpg_to_pdf else "application/pdf"
            storage_key = generate_input_storage_key(str(job_id), file_id, extension=file_ext)

            # Generate presigned upload URL
            upload_url = await storage_client.generate_presigned_upload_url(
                key=storage_key,
                expires_in=900,
                content_type=content_type,
            )

            file_entry = {
                "id": file_id,
                "original_name": sanitized_name,
                "size_bytes": f.size,
                "content_type": content_type,
                "storage_key": storage_key,
                "status": "pending",
                "uploaded_at": None,
                "sha256": None,
            }
            input_files_meta.append(file_entry)

            upload_items.append(
                PresignedUploadItem(
                    file_id=file_id,
                    upload_url=upload_url,
                    upload_method="PUT",
                    upload_headers={"Content-Type": content_type},
                    expires_in=900,
                )
            )

        new_job = Job(
            id=job_id,
            session_id=session_id,
            tool=payload.tool.lower(),
            status=JobStatus.PENDING,
            config=payload.config or {},
            input_files=input_files_meta,
            result_file=None,
            progress=0,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        session.add(new_job)
        await session.commit()
        await session.refresh(new_job)

        return JobCreateData(
            job=JobSummary(
                id=str(new_job.id),
                tool=new_job.tool,
                status=new_job.status.value,
                config=new_job.config,
                expires_at=new_job.expires_at,
                created_at=new_job.created_at,
            ),
            uploads=upload_items,
        )

    @staticmethod
    async def get_job(
        session: AsyncSession,
        job_id: str,
        session_id: str | None = None,
    ) -> Job:
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            raise AppException(status_code=404, code="JOB_NOT_FOUND", message="Job not found")

        stmt = select(Job).where(Job.id == job_uuid)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            raise AppException(status_code=404, code="JOB_NOT_FOUND", message="Job not found")

        # Session access control: Prevent unauthorized access to another session's job
        if session_id and job.session_id != session_id:
            raise AppException(
                status_code=403,
                code="ACCESS_DENIED",
                message="You do not have permission to access this job",
            )

        return job

    @staticmethod
    async def direct_upload_file(
        session: AsyncSession,
        job_id: str,
        file_id: str,
        content: bytes,
        filename: str | None = None,
        session_id: str | None = None,
        storage: StorageBackend | None = None,
    ) -> dict[str, Any]:
        """Allows direct binary upload to API server and validates content before storing."""
        job = await JobService.get_job(session, job_id, session_id)
        storage_client = storage or get_storage()

        if job.is_expired():
            raise AppException(
                status_code=410,
                code="FILE_EXPIRED",
                message="Job has expired and no longer accepts uploads",
            )

        if job.status not in (JobStatus.PENDING, JobStatus.UPLOADING):
            raise AppException(
                status_code=409,
                code="JOB_ALREADY_STARTED",
                message=f"Cannot upload files for job with status {job.status.value}",
            )

        file_meta = job.get_input_file(file_id)
        if not file_meta:
            raise AppException(
                status_code=404,
                code="FILE_NOT_FOUND",
                message=f"File {file_id} not registered for job {job_id}",
            )

        # Validate file content, size, and magic bytes
        is_jpg_to_pdf = job.tool.lower() in ("jpg_to_pdf", "jpg-to-pdf")
        is_pdf_to_jpg = job.tool.lower() in ("pdf_to_jpg", "pdf-to-jpg")

        if is_jpg_to_pdf:
            tool_max_mb = settings.JPG_TO_PDF_MAX_FILE_SIZE_MB
            max_size = tool_max_mb * 1024 * 1024
            validate_jpg_file(
                content=content,
                filename=filename or file_meta.get("original_name"),
                content_type=file_meta.get("content_type", "image/jpeg"),
                max_size_bytes=max_size,
            )
            # ClamAV Antivirus Scanning before storage persistence
            await scan_file_content(content, filename=filename or file_meta.get("original_name"))
            storage_key = file_meta["storage_key"]
            await storage_client.upload(key=storage_key, data=content, content_type="image/jpeg")
        else:
            tool_max_mb = settings.PDF_TO_JPG_MAX_FILE_SIZE_MB if is_pdf_to_jpg else settings.MAX_FILE_SIZE_MB
            max_size = tool_max_mb * 1024 * 1024
            validate_pdf_file(
                content=content,
                filename=filename or file_meta.get("original_name"),
                content_type="application/pdf",
                max_size_bytes=max_size,
            )
            # ClamAV Antivirus Scanning before storage persistence
            await scan_file_content(content, filename=filename or file_meta.get("original_name"))
            storage_key = file_meta["storage_key"]
            await storage_client.upload(key=storage_key, data=content, content_type="application/pdf")

        # Update file status and job status
        now_iso = datetime.now(UTC).isoformat()
        job.update_input_file(
            file_id,
            {
                "status": "uploaded",
                "size_bytes": len(content),
                "uploaded_at": now_iso,
                "security_scanned": True,
            },
        )

        if job.status == JobStatus.PENDING:
            job.transition_to(JobStatus.UPLOADING)

        await session.commit()
        await session.refresh(job)

        return job.get_input_file(file_id) or {}

    @staticmethod
    async def confirm_file_upload(
        session: AsyncSession,
        job_id: str,
        file_id: str,
        session_id: str | None = None,
        storage: StorageBackend | None = None,
    ) -> dict[str, Any]:
        """
        Validates that a presigned upload actually completed in Object Storage,
        inspects the stored file to verify magic bytes, and executes ClamAV malware scanning.
        """
        job = await JobService.get_job(session, job_id, session_id)
        storage_client = storage or get_storage()

        if job.is_expired():
            raise AppException(
                status_code=410,
                code="FILE_EXPIRED",
                message="Job has expired",
            )

        file_meta = job.get_input_file(file_id)
        if not file_meta:
            raise AppException(
                status_code=404,
                code="FILE_NOT_FOUND",
                message=f"File {file_id} not found in job {job_id}",
            )

        storage_key = file_meta["storage_key"]
        exists = await storage_client.exists(key=storage_key)
        if not exists:
            raise AppException(
                status_code=404,
                code="FILES_NOT_READY",
                message=f"File {file_id} has not been uploaded to storage yet",
            )

        # Validate stored content (magic bytes) and scan for malware
        try:
            stored_data = await storage_client.download(key=storage_key)
            is_jpg_to_pdf = job.tool.lower() in ("jpg_to_pdf", "jpg-to-pdf")
            if is_jpg_to_pdf:
                if not validate_jpg_magic_bytes(stored_data):
                    await storage_client.delete(key=storage_key)
                    raise AppException(
                        status_code=415,
                        code="INVALID_CONTENT_TYPE",
                        message="Uploaded file is not a valid JPEG image (invalid magic bytes signature)",
                    )
            else:
                if not validate_pdf_magic_bytes(stored_data):
                    # Invalid content: clean up and raise
                    await storage_client.delete(key=storage_key)
                    raise AppException(
                        status_code=415,
                        code="INVALID_CONTENT_TYPE",
                        message="Uploaded file is not a valid PDF (invalid magic bytes signature)",
                    )

            # ClamAV Antivirus Scan: If infected, purge object from storage immediately
            await scan_file_content(stored_data, filename=file_meta.get("original_name"))
            actual_size = len(stored_data)
        except AppException:
            # Purge stored object if invalid content or malware detected
            try:
                await storage_client.delete(key=storage_key)
            except Exception:
                pass
            raise
        except Exception as e:
            raise AppException(
                status_code=500,
                code="STORAGE_ERROR",
                message=f"Could not verify file content: {str(e)}",
            )

        now_iso = datetime.now(UTC).isoformat()
        job.update_input_file(
            file_id,
            {
                "status": "verified",
                "size_bytes": actual_size,
                "uploaded_at": now_iso,
                "security_scanned": True,
            },
        )

        if job.status == JobStatus.PENDING:
            job.transition_to(JobStatus.UPLOADING)

        await session.commit()
        await session.refresh(job)

        return job.get_input_file(file_id) or {}

    @staticmethod
    async def start_job(
        session: AsyncSession,
        job_id: str,
        payload: JobStartRequest | None = None,
        session_id: str | None = None,
        storage: StorageBackend | None = None,
    ) -> JobStartData:
        job = await JobService.get_job(session, job_id, session_id)
        storage_client = storage or get_storage()

        if job.is_expired():
            raise AppException(
                status_code=410,
                code="FILE_EXPIRED",
                message="Cannot start expired job",
            )

        if job.status in (JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.COMPLETED):
            raise AppException(
                status_code=409,
                code="JOB_ALREADY_STARTED",
                message=f"Job is already in {job.status.value} state",
            )

        # Verify all input files are uploaded, exist in storage, and passed security verification
        unready_files: list[str] = []
        unverified_files: list[str] = []
        for f in job.input_files or []:
            key = f.get("storage_key")
            if not key or not await storage_client.exists(key=key):
                unready_files.append(f.get("original_name", f.get("id")))
            elif not f.get("security_scanned") or f.get("status") not in ("uploaded", "verified"):
                unverified_files.append(f.get("original_name", f.get("id")))

        if unready_files:
            raise AppException(
                status_code=409,
                code="FILES_NOT_READY",
                message=f"The following files are not uploaded yet: {', '.join(unready_files)}",
            )

        if unverified_files:
            raise AppException(
                status_code=400,
                code="SECURITY_CHECK_REQUIRED",
                message=f"The following files have not passed required security verification: {', '.join(unverified_files)}",
            )

        # Update config if provided, ensuring sensitive passwords are NEVER stored in PostgreSQL
        ephemeral_password = None
        if payload and payload.config:
            cfg = dict(payload.config)
            if "password" in cfg:
                raw_pw = cfg.pop("password", None)
                if raw_pw and isinstance(raw_pw, str):
                    ephemeral_password = raw_pw
            if "confirm_password" in cfg:
                cfg.pop("confirm_password", None)
            job.config = {**job.config, **cfg}

        # Store ephemeral password in Redis with 300s TTL (never in DB)
        if ephemeral_password:
            try:
                import redis.asyncio as aioredis
                temp_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                try:
                    await temp_redis.setex(f"ephemeral_job_password:{job.id}", 300, ephemeral_password)
                finally:
                    await temp_redis.aclose()
            except Exception as e:
                logger.warning(f"Could not store ephemeral password in Redis: {e}")

        # Transition to QUEUED
        job.transition_to(JobStatus.QUEUED)
        await session.commit()
        await session.refresh(job)

        # Enqueue background task
        try:
            from app.tools.registry import TOOL_REGISTRY
            from app.workers.tasks import process_job_task, test_job_task

            if job.tool.lower() in TOOL_REGISTRY:
                process_job_task.delay(str(job.id))
            else:
                test_job_task.delay(str(job.id))
        except Exception as e:
            logger.warning(f"Could not dispatch Celery task asynchronously: {e}")

        return JobStartData(
            id=str(job.id),
            status=job.status.value,
            estimated_duration_seconds=5,
        )

    @staticmethod
    async def cancel_job(
        session: AsyncSession,
        job_id: str,
        session_id: str | None = None,
    ) -> Job:
        job = await JobService.get_job(session, job_id, session_id)
        if job.status in (JobStatus.COMPLETED, JobStatus.EXPIRED, JobStatus.CANCELLED):
            raise AppException(
                status_code=409,
                code="INVALID_STATE_TRANSITION",
                message=f"Cannot cancel job in {job.status.value} state",
            )

        job.transition_to(JobStatus.CANCELLED)
        await session.commit()
        await session.refresh(job)
        try:
            from app.core.redis import publish_job_progress
            await publish_job_progress(job_id, {
                "job_id": job_id,
                "status": "cancelled",
                "progress": job.progress,
            })
        except Exception:
            pass
        return job

    @staticmethod
    async def get_job_download(
        session: AsyncSession,
        job_id: str,
        session_id: str | None = None,
        storage: StorageBackend | None = None,
    ) -> JobDownloadData:
        job = await JobService.get_job(session, job_id, session_id)
        storage_client = storage or get_storage()

        if job.is_expired():
            raise AppException(
                status_code=410,
                code="FILE_EXPIRED",
                message="File has expired and has been deleted",
            )

        if job.status != JobStatus.COMPLETED:
            raise AppException(
                status_code=400,
                code="JOB_NOT_COMPLETED",
                message=f"Job is not completed yet (current status: {job.status.value})",
            )

        if not job.result_file or not job.result_file.get("storage_key"):
            raise AppException(
                status_code=404,
                code="FILE_NOT_FOUND",
                message="Result file not found for this job",
            )

        result = job.result_file
        storage_key = result["storage_key"]
        filename = result.get("original_name", "output.pdf")

        download_url = await storage_client.generate_presigned_download_url(
            key=storage_key,
            expires_in=300,
            filename=filename,
        )

        return JobDownloadData(
            download_url=download_url,
            expires_in=300,
            filename=filename,
            size_bytes=result.get("size_bytes", 0),
            content_type=result.get("content_type", "application/pdf"),
        )

    @staticmethod
    async def cleanup_expired_jobs(
        session: AsyncSession,
        storage: StorageBackend | None = None,
    ) -> int:
        """Finds expired jobs, safely removes their files from storage, and marks them EXPIRED."""
        storage_client = storage or get_storage()
        now = datetime.now(UTC)

        stmt = select(Job).where(
            Job.expires_at <= now,
            Job.status != JobStatus.EXPIRED,
        )
        result = await session.execute(stmt)
        expired_jobs = result.scalars().all()

        cleaned_count = 0
        for job in expired_jobs:
            keys_to_delete: list[str] = []
            for f in job.input_files or []:
                if f.get("storage_key"):
                    keys_to_delete.append(f["storage_key"])

            if job.result_file and job.result_file.get("storage_key"):
                keys_to_delete.append(job.result_file["storage_key"])

            # Delete objects safely
            for k in keys_to_delete:
                try:
                    await storage_client.delete(k)
                except Exception as e:
                    logger.warning(f"Error deleting key {k} during cleanup: {e}")

            try:
                job.transition_to(JobStatus.EXPIRED)
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"Could not transition job {job.id} to EXPIRED: {e}")

        await session.commit()
        return cleaned_count
