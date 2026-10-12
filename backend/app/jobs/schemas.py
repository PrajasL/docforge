from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FileInputRequest(BaseModel):
    name: str = Field(..., description="Original filename with allowed extension (.pdf, .jpg, .jpeg)")
    size: int = Field(..., gt=0, description="Size of file in bytes")
    content_type: str = Field("application/pdf", description="MIME type")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not (v.lower().endswith(".pdf") or v.lower().endswith(".jpg") or v.lower().endswith(".jpeg")):
            raise ValueError("File must have a valid extension (.pdf, .jpg, or .jpeg)")
        return v


class JobCreateRequest(BaseModel):
    tool: str = Field(..., min_length=1, max_length=50, description="Tool identifier (e.g., merge, test)")
    files: list[FileInputRequest] = Field(..., min_length=1, description="List of files to upload")
    config: dict[str, Any] = Field(default_factory=dict, description="Tool-specific configuration")


class PresignedUploadItem(BaseModel):
    file_id: str
    upload_url: str
    upload_method: str = "PUT"
    upload_headers: dict[str, str] = Field(default_factory=lambda: {"Content-Type": "application/pdf"})
    expires_in: int = 900


class JobSummary(BaseModel):
    id: str
    tool: str
    status: str
    config: dict[str, Any]
    expires_at: datetime
    created_at: datetime


class JobCreateData(BaseModel):
    job: JobSummary
    uploads: list[PresignedUploadItem]


class JobStartRequest(BaseModel):
    config: dict[str, Any] | None = None


class JobStartData(BaseModel):
    id: str
    status: str
    estimated_duration_seconds: int = 5


class JobDetailData(BaseModel):
    id: str
    tool: str
    status: str
    progress: int
    config: dict[str, Any]
    input_files: list[dict[str, Any]]
    result_file: dict[str, Any] | None = None
    error_message: str | None = None
    error_code: str | None = None
    error_details: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime
    created_at: datetime


class JobDownloadData(BaseModel):
    download_url: str
    expires_in: int = 300
    filename: str
    size_bytes: int
    content_type: str = "application/pdf"
