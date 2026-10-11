from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    id: str
    original_name: str
    size_bytes: int
    content_type: str = "application/pdf"
    storage_key: str
    status: str = Field(default="pending")  # pending, uploaded, verified, failed
    sha256: Optional[str] = None
    page_count: Optional[int] = None
    uploaded_at: Optional[datetime] = None


class PresignedUploadInfo(BaseModel):
    file_id: str
    upload_url: str
    upload_method: str = "PUT"
    upload_headers: dict[str, str] = Field(
        default_factory=lambda: {"Content-Type": "application/pdf"}
    )
    expires_in: int = 900
