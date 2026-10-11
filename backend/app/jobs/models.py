import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set

from sqlalchemy import (
    Column,
    String,
    Text,
    SmallInteger,
    Integer,
    DateTime,
    Index,
    Enum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import validates

from app.core.database import Base
from app.core.errors import AppException


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class InvalidJobTransitionError(AppException):
    def __init__(self, current: JobStatus, target: JobStatus) -> None:
        super().__init__(
            status_code=409,
            code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition job from '{current.value}' to '{target.value}'.",
        )


# Valid transition state machine
VALID_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.PENDING: {
        JobStatus.UPLOADING,
        JobStatus.QUEUED,
        JobStatus.CANCELLED,
        JobStatus.EXPIRED,
    },
    JobStatus.UPLOADING: {
        JobStatus.QUEUED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.EXPIRED,
    },
    JobStatus.QUEUED: {
        JobStatus.PROCESSING,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.EXPIRED,
    },
    JobStatus.PROCESSING: {
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.EXPIRED,
    },
    JobStatus.FAILED: {
        JobStatus.QUEUED,  # Safe retry transition
        JobStatus.EXPIRED,
    },
    JobStatus.COMPLETED: {
        JobStatus.EXPIRED,
    },
    JobStatus.CANCELLED: {
        JobStatus.EXPIRED,
    },
    JobStatus.EXPIRED: set(),  # Terminal state
}


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    session_id = Column(String(255), nullable=False, index=True)
    tool = Column(String(50), nullable=False, index=True)
    status = Column(
        Enum(
            JobStatus,
            name="job_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    config = Column(JSONB, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_details = Column(JSONB, nullable=True)
    progress = Column(SmallInteger, default=0, nullable=False)
    input_files = Column(JSONB, nullable=False, default=list)
    result_file = Column(JSONB, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_jobs_tool_created", "tool", "created_at"),
    )

    def __init__(self, **kwargs: Any) -> None:
        if "retry_count" not in kwargs:
            kwargs["retry_count"] = 0
        if "progress" not in kwargs:
            kwargs["progress"] = 0
        if "status" not in kwargs:
            kwargs["status"] = JobStatus.PENDING
        if "config" not in kwargs:
            kwargs["config"] = {}
        if "input_files" not in kwargs:
            kwargs["input_files"] = []
        super().__init__(**kwargs)

    def transition_to(
        self,
        target_status: JobStatus,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Enforces the job state machine transitions and updates timestamps."""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if target_status not in allowed:
            raise InvalidJobTransitionError(self.status, target_status)

        now = datetime.now(timezone.utc)
        old_status = self.status
        self.status = target_status

        if target_status == JobStatus.PROCESSING and not self.started_at:
            self.started_at = now
        elif target_status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            self.completed_at = now

        if target_status == JobStatus.QUEUED and old_status == JobStatus.FAILED:
            self.retry_count = (self.retry_count or 0) + 1

        if error_message:
            self.error_message = error_message
        if error_code:
            self.error_code = error_code
        if error_details:
            self.error_details = error_details

    def is_expired(self) -> bool:
        """Returns True if the job has passed its expiration time or is in EXPIRED state."""
        if self.status == JobStatus.EXPIRED:
            return True
        now = datetime.now(timezone.utc)
        if self.expires_at and self.expires_at <= now:
            return True
        return False

    def add_input_file(self, file_meta: Dict[str, Any]) -> None:
        """Appends a new file entry to the input_files list."""
        current = list(self.input_files or [])
        current.append(file_meta)
        self.input_files = current

    def get_input_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        for f in self.input_files or []:
            if f.get("id") == file_id:
                return f
        return None

    def update_input_file(self, file_id: str, updates: Dict[str, Any]) -> bool:
        current = list(self.input_files or [])
        found = False
        for i, f in enumerate(current):
            if f.get("id") == file_id:
                current[i] = {**f, **updates}
                found = True
                break
        if found:
            self.input_files = current
        return found

    def all_files_uploaded(self) -> bool:
        if not self.input_files:
            return False
        return all(f.get("status") in ("uploaded", "verified") for f in self.input_files)
