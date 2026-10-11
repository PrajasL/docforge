import hashlib
import os
import re
from typing import Optional
from app.core.config import settings
from app.core.errors import AppException


PDF_MAGIC_BYTES = b"%PDF-"
PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}

JPG_MAGIC_BYTES = b"\xff\xd8\xff"
JPG_MIME_TYPES = {"image/jpeg", "image/jpg", "image/pjpeg"}
JPG_EXTENSIONS = {".jpg", ".jpeg"}


from app.core.scanner import scanner, ScanResult


class FileValidationError(AppException):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(status_code=status_code, code=code, message=message)


def sanitize_filename(filename: Optional[str], default_ext: str = ".pdf") -> str:
    """Sanitizes user-provided filename to prevent path traversal, null byte injections, and shell escapes."""
    if not filename:
        return f"document{default_ext}"
    
    # Strip null bytes and control chars upfront
    cleaned = filename.replace("\x00", "").replace("\r", "").replace("\n", "").strip()
    # Strip any paths (Windows & POSIX)
    cleaned = os.path.basename(cleaned.replace("\\", "/")).strip()
    # Remove control characters, backslashes, etc.
    cleaned = re.sub(r'[^\w\s\.-]', '_', cleaned)
    # Collapse multiple consecutive dots to prevent path traversal like ...
    cleaned = re.sub(r'\.{2,}', '.', cleaned)
    base, ext = os.path.splitext(cleaned)
    # Ensure allowed extension
    if ext.lower() not in ({".pdf"} | JPG_EXTENSIONS):
        cleaned = f"{cleaned}{default_ext}"
    # Limit length
    if len(cleaned) > 120:
        base, ext = os.path.splitext(cleaned)
        cleaned = f"{base[:110]}{ext}"
    return cleaned or f"document{default_ext}"


async def scan_file_content(content: bytes, filename: Optional[str] = None) -> ScanResult:
    """
    Scans file content using ClamAV antivirus engine.
    Raises FileValidationError with status 400 if malware signature is detected.
    """
    result = await scanner.scan_bytes(content)
    if not result.is_clean:
        raise FileValidationError(
            code="MALWARE_DETECTED",
            message=f"Malicious content detected in file '{filename or 'uploaded'}': {result.virus_name}",
            status_code=400,
        )
    return result


def validate_file_extension(filename: str) -> bool:
    """Checks whether the file has a .pdf extension."""
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() == ".pdf"


def validate_jpg_extension(filename: str) -> bool:
    """Checks whether the file has a .jpg or .jpeg extension."""
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in JPG_EXTENSIONS


def validate_jpg_content_type(content_type: str) -> bool:
    """Checks whether the MIME type is a JPEG content type."""
    if not content_type:
        return False
    return content_type.strip().lower() in JPG_MIME_TYPES


def validate_jpg_magic_bytes(data: bytes) -> bool:
    """
    Validates that the file begins with the JPEG SOI (Start of Image) marker: 0xFF, 0xD8, 0xFF.
    """
    if not data or len(data) < 3:
        return False
    return data[:3] == JPG_MAGIC_BYTES


def validate_content_type(content_type: str) -> bool:
    """Checks whether the MIME type is a PDF content type."""
    if not content_type:
        return False
    return content_type.strip().lower() in PDF_MIME_TYPES


def validate_pdf_magic_bytes(data: bytes) -> bool:
    """
    Validates that the file contains the %PDF- header within the first 1024 bytes
    per the PDF specification (ISO 32000-1).
    """
    if not data or len(data) < 5:
        return False
    header_chunk = data[:1024]
    return PDF_MAGIC_BYTES in header_chunk


def calculate_sha256(data: bytes) -> str:
    """Calculates SHA-256 hex digest of file data."""
    return hashlib.sha256(data).hexdigest()


def validate_pdf_file(
    content: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
) -> None:
    """
    Performs comprehensive validation on a PDF file:
    - Non-empty
    - Size within allowed limit
    - Valid extension (if filename provided)
    - Valid content type (if content_type provided)
    - Valid PDF magic bytes in actual file content
    """
    if not content or len(content) == 0:
        raise FileValidationError(
            code="VALIDATION_ERROR",
            message="Uploaded file is empty (0 bytes)",
            status_code=422,
        )

    limit = max_size_bytes or (settings.MAX_FILE_SIZE_MB * 1024 * 1024)
    if len(content) > limit:
        raise FileValidationError(
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum allowed size of {limit // (1024 * 1024)} MB",
            status_code=413,
        )

    if filename and not validate_file_extension(filename):
        raise FileValidationError(
            code="INVALID_CONTENT_TYPE",
            message=f"File '{filename}' does not have a valid .pdf extension",
            status_code=415,
        )

    if content_type and not validate_content_type(content_type):
        raise FileValidationError(
            code="INVALID_CONTENT_TYPE",
            message=f"Invalid MIME type '{content_type}'. Expected 'application/pdf'",
            status_code=415,
        )

    if not validate_pdf_magic_bytes(content):
        raise FileValidationError(
            code="INVALID_CONTENT_TYPE",
            message="File content is not a valid PDF document (missing %PDF- header signature)",
            status_code=415,
        )


def validate_jpg_file(
    content: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
) -> None:
    """
    Performs comprehensive validation on a JPG/JPEG image file:
    - Non-empty
    - Size within allowed limit
    - Valid extension (.jpg or .jpeg) if filename provided
    - Valid content type (image/jpeg, etc.) if content_type provided
    - Valid JPEG magic bytes (0xFF, 0xD8, 0xFF) in actual file content
    - Decodable/non-corrupted image verified with PIL
    """
    if not content or len(content) == 0:
        raise FileValidationError(
            code="VALIDATION_ERROR",
            message="Uploaded file is empty (0 bytes)",
            status_code=422,
        )

    limit = max_size_bytes or (settings.JPG_TO_PDF_MAX_FILE_SIZE_MB * 1024 * 1024)
    if len(content) > limit:
        raise FileValidationError(
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum allowed size of {limit // (1024 * 1024)} MB",
            status_code=413,
        )

    if filename and not validate_jpg_extension(filename):
        raise FileValidationError(
            code="INVALID_CONTENT_TYPE",
            message=f"File '{filename}' does not have a valid .jpg or .jpeg extension",
            status_code=415,
        )

    if content_type and not validate_jpg_content_type(content_type):
        raise FileValidationError(
            code="INVALID_CONTENT_TYPE",
            message=f"Invalid MIME type '{content_type}'. Expected 'image/jpeg'",
            status_code=415,
        )

    if not validate_jpg_magic_bytes(content):
        raise FileValidationError(
            code="INVALID_CONTENT_TYPE",
            message="File content is not a valid JPEG image (missing JPEG SOI marker)",
            status_code=415,
        )

    # Validate image data integrity using PIL
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except Exception:
        raise FileValidationError(
            code="INVALID_FILE",
            message=f"Image file '{filename or 'unknown'}' is corrupted or unreadable",
            status_code=422,
        )

