import pytest
from unittest.mock import patch
from app.core.config import settings
from app.core.errors import AppException
from app.core.scanner import ClamAVScanner, EICAR_SIGNATURE, ScannerException
from app.files.validator import sanitize_filename, FileValidationError
from app.jobs.models import Job, JobStatus
from app.jobs.schemas import JobCreateRequest, FileInputRequest
from app.jobs.service import JobService
from app.core.storage import InMemoryStorageBackend
from app.workers.tasks import _async_process_job


def test_sanitize_filename_prevents_path_traversal():
    # Unix traversal
    assert sanitize_filename("../../../etc/shadow.pdf") == "shadow.pdf"
    # Windows traversal
    assert sanitize_filename(r"..\\..\\Windows\\System32\\cmd.exe.pdf") == "cmd.exe.pdf"
    # Null byte injection
    assert sanitize_filename("test\x00injection.pdf") == "testinjection.pdf"
    # Multiple dot traversal pattern
    assert sanitize_filename("....//hidden.pdf") == "hidden.pdf"
    # Empty or None defaults safely
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename(None) == "document.pdf"


def test_zero_byte_file_rejected_at_job_create():
    with pytest.raises(Exception) as exc:
        FileInputRequest(name="empty.pdf", size=0)
    assert "greater than 0" in str(exc.value)


@pytest.mark.asyncio
async def test_aggregate_job_size_limit_rejected(db_session):
    orig_limit = settings.MAX_AGGREGATE_JOB_SIZE_MB
    settings.MAX_AGGREGATE_JOB_SIZE_MB = 10  # 10 MB limit for test
    try:
        # Two 6 MB files total 12 MB > 10 MB limit
        payload = JobCreateRequest(
            tool="merge",
            files=[
                FileInputRequest(name="doc1.pdf", size=6 * 1024 * 1024),
                FileInputRequest(name="doc2.pdf", size=6 * 1024 * 1024),
            ],
        )
        with pytest.raises(AppException) as exc:
            await JobService.create_job(db_session, payload, session_id="test_sess")
        assert exc.value.status_code == 413
        assert exc.value.code == "PAYLOAD_TOO_LARGE"
    finally:
        settings.MAX_AGGREGATE_JOB_SIZE_MB = orig_limit


@pytest.mark.asyncio
async def test_eicar_test_signature_detected():
    scanner = ClamAVScanner(enabled=True)
    # EICAR signature inside dummy PDF header
    fake_infected = b"%PDF-1.4\n" + EICAR_SIGNATURE + b"\n%%EOF"
    result = await scanner.scan_bytes(fake_infected)

    assert result.is_clean is False
    assert result.virus_name == "Eicar-Test-Signature"
    assert result.scanned is True


@pytest.mark.asyncio
async def test_scanner_outage_fail_closed_in_production():
    # Scanner points to non-existent port with fail_closed=True
    scanner = ClamAVScanner(
        host="127.0.0.1",
        port=59999,
        timeout=0.2,
        enabled=True,
        fail_closed=True,
    )
    with pytest.raises(ScannerException) as exc:
        await scanner.scan_bytes(b"%PDF-1.4\nclean test file\n%%EOF")
    assert exc.value.status_code == 503
    assert exc.value.code == "SCANNER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_scanner_outage_fail_open_in_dev():
    # In development mode with fail_closed=False
    scanner = ClamAVScanner(
        host="127.0.0.1",
        port=59999,
        timeout=0.2,
        enabled=True,
        fail_closed=False,
    )
    orig_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "development"
    try:
        result = await scanner.scan_bytes(b"%PDF-1.4\nclean test file\n%%EOF")
        assert result.is_clean is True
        assert result.scanned is False
        assert "unavailable" in (result.details or "").lower()
    finally:
        settings.ENVIRONMENT = orig_env


@pytest.mark.asyncio
async def test_direct_upload_eicar_rejected_with_malware_detected(db_session):
    storage = InMemoryStorageBackend()
    payload = JobCreateRequest(
        tool="merge",
        files=[FileInputRequest(name="doc1.pdf", size=1024)],
    )
    job_data = await JobService.create_job(db_session, payload, session_id="test_sess", storage=storage)
    job_id = job_data.job.id
    file_id = job_data.uploads[0].file_id

    infected_content = b"%PDF-1.4\n" + EICAR_SIGNATURE + b"\n%%EOF"

    with pytest.raises(FileValidationError) as exc:
        await JobService.direct_upload_file(
            db_session,
            job_id=job_id,
            file_id=file_id,
            content=infected_content,
            filename="doc1.pdf",
            session_id="test_sess",
            storage=storage,
        )
    assert exc.value.status_code == 400
    assert exc.value.code == "MALWARE_DETECTED"


@pytest.mark.asyncio
async def test_confirm_upload_eicar_purges_storage_and_rejects(db_session):
    storage = InMemoryStorageBackend()
    payload = JobCreateRequest(
        tool="merge",
        files=[FileInputRequest(name="doc1.pdf", size=1024)],
    )
    job_data = await JobService.create_job(db_session, payload, session_id="test_sess", storage=storage)
    job_id = job_data.job.id
    file_id = job_data.uploads[0].file_id

    job = await JobService.get_job(db_session, job_id, session_id="test_sess")
    storage_key = job.get_input_file(file_id)["storage_key"]

    # Pre-upload infected file to storage as if from presigned PUT
    infected_content = b"%PDF-1.4\n" + EICAR_SIGNATURE + b"\n%%EOF"
    await storage.upload(storage_key, infected_content, "application/pdf")
    assert await storage.exists(storage_key) is True

    with pytest.raises(FileValidationError) as exc:
        await JobService.confirm_file_upload(
            db_session,
            job_id=job_id,
            file_id=file_id,
            session_id="test_sess",
            storage=storage,
        )
    assert exc.value.status_code == 400
    assert exc.value.code == "MALWARE_DETECTED"

    # Crucial security guarantee: object must have been purged from storage
    assert await storage.exists(storage_key) is False


@pytest.mark.asyncio
async def test_worker_rejects_unscanned_files(db_session):
    storage = InMemoryStorageBackend()
    payload = JobCreateRequest(
        tool="merge",
        files=[
            FileInputRequest(name="doc1.pdf", size=1024),
            FileInputRequest(name="doc2.pdf", size=1024),
        ],
    )
    job_data = await JobService.create_job(db_session, payload, session_id="test_sess", storage=storage)
    job_id = job_data.job.id

    job = await JobService.get_job(db_session, job_id, session_id="test_sess")
    # Mark files as uploaded but NOT security_scanned, and set job to QUEUED
    for f in job.input_files:
        f["status"] = "uploaded"
        f["security_scanned"] = False

    job.status = JobStatus.QUEUED
    await db_session.commit()

    with patch("app.workers.tasks.get_storage", return_value=storage):
        with pytest.raises(AppException) as exc:
            await _async_process_job(job_id)
        assert exc.value.code == "UNSCANNED_FILE_REJECTED"
