import hashlib
import os
from typing import Any

import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ProcessingContext, ToolHandler


class ProtectPDFHandler(ToolHandler):
    """
    Handler for encrypting and password-protecting PDF documents.
    Uses industry-standard AES-256 encryption to require a user password
    to view and open the document.
    """

    tool_id = "protect"
    display_name = "Protect PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validates password protection configuration."""
        if not config:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Password protection configuration is required.",
            )

        password = config.get("password")
        if not password or not isinstance(password, str) or not password.strip():
            raise AppException(
                status_code=400,
                code="INVALID_PASSWORD",
                message="Password cannot be empty.",
            )

        if len(password) > 128:
            raise AppException(
                status_code=400,
                code="INVALID_PASSWORD",
                message="Password cannot exceed 128 characters.",
            )

        confirm_password = config.get("confirm_password")
        if confirm_password is not None and confirm_password != password:
            raise AppException(
                status_code=400,
                code="PASSWORD_MISMATCH",
                message="Password and confirmation password do not match.",
            )

    async def process(self, context: ProcessingContext) -> dict[str, Any]:
        """Executes PDF encryption pipeline using AES-256."""
        # 1. Validate input file
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Protect PDF requires exactly 1 input file.",
            )

        file_meta = context.input_files[0]
        local_path = file_meta.get("local_path")
        original_name = file_meta.get("original_name", "document.pdf")

        if not local_path or not os.path.exists(local_path):
            raise AppException(
                status_code=404,
                code="FILE_NOT_FOUND",
                message=f"Input file not found on worker: {original_name}",
            )

        file_size = os.path.getsize(local_path)
        if file_size == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_INPUT_FILE",
                message=f"Input file '{original_name}' is empty (0 bytes).",
            )

        # 2. Extract and validate configuration
        config = context.config or {}
        self.validate_config(config)

        password = str(config.get("password"))
        algorithm = "AES-256"

        # 3. Read input PDF
        try:
            reader = pypdf.PdfReader(local_path)
        except (PdfReadError, PdfStreamError, PyPdfError, Exception) as e:
            raise AppException(
                status_code=400,
                code="CORRUPTED_FILE",
                message=f"File '{original_name}' is corrupted or not a valid PDF: {str(e)}",
            )

        # Check if already encrypted
        if reader.is_encrypted:
            raise AppException(
                status_code=400,
                code="ALREADY_ENCRYPTED",
                message=f"File '{original_name}' is already password-protected.",
            )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_DOCUMENT",
                message=f"File '{original_name}' has 0 pages and cannot be processed.",
            )

        # 4. Construct encrypted PDF
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        # Apply AES-256 encryption
        try:
            writer.encrypt(user_password=password, algorithm=algorithm)
        except Exception as e:
            raise AppException(
                status_code=500,
                code="ENCRYPTION_ERROR",
                message=f"Failed to encrypt PDF with {algorithm}: {str(e)}",
            )

        # 5. Save output file
        custom_name = config.get("output_filename")
        if custom_name and isinstance(custom_name, str) and custom_name.strip():
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
            output_filename = safe_name
        else:
            base_name, _ = os.path.splitext(original_name)
            output_filename = f"protected_{base_name}.pdf"

        output_path = os.path.join(context.temp_dir, f"protect_{context.job_id}.pdf")

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        out_size = os.path.getsize(output_path)
        sha256 = hashlib.sha256()
        with open(output_path, "rb") as f_out:
            while chunk := f_out.read(65536):
                sha256.update(chunk)

        # Explicitly clear temporary password reference
        del password

        return {
            "output_path": output_path,
            "local_path": output_path,
            "filename": output_filename,
            "size_bytes": out_size,
            "page_count": total_pages,
            "is_encrypted": True,
            "encryption_algorithm": algorithm,
            "sha256": sha256.hexdigest(),
            "content_type": "application/pdf",
        }
