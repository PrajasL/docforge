from datetime import datetime
from typing import List, Optional, Dict, Any
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
    files: List[FileInputRequest] = Field(..., min_length=1, description="List of files to upload")
    config: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific configuration")


class PresignedUploadItem(BaseModel):
    file_id: str
    upload_url: str
    upload_method: str = "PUT"
    upload_headers: Dict[str, str] = Field(default_factory=lambda: {"Content-Type": "application/pdf"})
    expires_in: int = 900


class JobSummary(BaseModel):
    id: str
    tool: str
    status: str
    config: Dict[str, Any]
    expires_at: datetime
    created_at: datetime


class JobCreateData(BaseModel):
    job: JobSummary
    uploads: List[PresignedUploadItem]


class JobStartRequest(BaseModel):
    config: Optional[Dict[str, Any]] = None


class JobStartData(BaseModel):
    id: str
    status: str
    estimated_duration_seconds: int = 5


class JobDetailData(BaseModel):
    id: str
    tool: str
    status: str
    progress: int
    config: Dict[str, Any]
    input_files: List[Dict[str, Any]]
    result_file: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime


class JobDownloadData(BaseModel):
    download_url: str
    expires_in: int = 300
    filename: str
    size_bytes: int
    content_type: str = "application/pdf"
