import uuid
from datetime import datetime, timezone, timedelta
import pytest
from app.jobs.models import Job, JobStatus, InvalidJobTransitionError


def create_test_job(status: JobStatus = JobStatus.PENDING) -> Job:
    now = datetime.now(timezone.utc)
    return Job(
        id=uuid.uuid4(),
        session_id="test-session-123",
        tool="merge",
        status=status,
        config={},
        input_files=[
            {"id": "file-1", "original_name": "doc1.pdf", "status": "pending", "storage_key": "k1"}
        ],
        expires_at=now + timedelta(hours=2),
    )


def test_job_valid_lifecycle_transitions():
    job = create_test_job(JobStatus.PENDING)
    assert job.status == JobStatus.PENDING
    assert job.started_at is None
    assert job.completed_at is None

    # PENDING -> UPLOADING
    job.transition_to(JobStatus.UPLOADING)
    assert job.status == JobStatus.UPLOADING

    # UPLOADING -> QUEUED
    job.transition_to(JobStatus.QUEUED)
    assert job.status == JobStatus.QUEUED

    # QUEUED -> PROCESSING
    job.transition_to(JobStatus.PROCESSING)
    assert job.status == JobStatus.PROCESSING
    assert job.started_at is not None

    # PROCESSING -> COMPLETED
    job.transition_to(JobStatus.COMPLETED)
    assert job.status == JobStatus.COMPLETED
    assert job.completed_at is not None

    # COMPLETED -> EXPIRED
    job.transition_to(JobStatus.EXPIRED)
    assert job.status == JobStatus.EXPIRED


def test_job_failure_and_retry_transitions():
    job = create_test_job(JobStatus.QUEUED)
    job.transition_to(JobStatus.PROCESSING)

    # Fail
    job.transition_to(
        JobStatus.FAILED,
        error_message="Worker timeout",
        error_code="TIMEOUT",
    )
    assert job.status == JobStatus.FAILED
    assert job.error_message == "Worker timeout"
    assert job.error_code == "TIMEOUT"
    assert job.retry_count == 0

    # Retry back to QUEUED
    job.transition_to(JobStatus.QUEUED)
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 1


def test_job_cancellation():
    job = create_test_job(JobStatus.PENDING)
    job.transition_to(JobStatus.CANCELLED)
    assert job.status == JobStatus.CANCELLED

    job_queued = create_test_job(JobStatus.QUEUED)
    job_queued.transition_to(JobStatus.CANCELLED)
    assert job_queued.status == JobStatus.CANCELLED


def test_invalid_transitions_raise_error():
    job = create_test_job(JobStatus.PENDING)
    # Cannot jump directly to COMPLETED
    with pytest.raises(InvalidJobTransitionError):
        job.transition_to(JobStatus.COMPLETED)

    # Cannot transition from EXPIRED (terminal)
    job_expired = create_test_job(JobStatus.EXPIRED)
    with pytest.raises(InvalidJobTransitionError):
        job_expired.transition_to(JobStatus.PENDING)

    # Cannot transition from COMPLETED to QUEUED
    job_completed = create_test_job(JobStatus.COMPLETED)
    with pytest.raises(InvalidJobTransitionError):
        job_completed.transition_to(JobStatus.QUEUED)


def test_job_expiration_helpers():
    now = datetime.now(timezone.utc)
    # Not expired
    job = Job(
        status=JobStatus.PENDING,
        expires_at=now + timedelta(hours=1),
    )
    assert job.is_expired() is False

    # Past expires_at
    expired_job = Job(
        status=JobStatus.PENDING,
        expires_at=now - timedelta(minutes=5),
    )
    assert expired_job.is_expired() is True

    # In EXPIRED status
    marked_expired = Job(
        status=JobStatus.EXPIRED,
        expires_at=now + timedelta(hours=1),
    )
    assert marked_expired.is_expired() is True


def test_job_input_file_helpers():
    job = create_test_job(JobStatus.PENDING)
    assert job.all_files_uploaded() is False

    # Update input file
    success = job.update_input_file("file-1", {"status": "verified"})
    assert success is True
    assert job.all_files_uploaded() is True

    # Retrieve
    f = job.get_input_file("file-1")
    assert f is not None
    assert f["status"] == "verified"

    # Non-existent
    assert job.get_input_file("non-existent") is None
