import hashlib
import os
from typing import Dict, Any
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


class UnlockPDFHandler(ToolHandler):
    """
    Handler for removing password protection from PDF documents.
    Verifies the supplied password, decrypts the document streams,
    and produces a clean, unencrypted output PDF.
    """

    tool_id = "unlock"
    display_name = "Unlock PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates unlock configuration and password parameter."""
        if not config:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Unlock configuration is required.",
            )

        password = config.get("password")
        if not password or not isinstance(password, str) or not password.strip():
            raise AppException(
                status_code=400,
                code="INVALID_PASSWORD",
                message="Password is required to unlock this PDF.",
            )

        if len(password) > 128:
            raise AppException(
                status_code=400,
                code="INVALID_PASSWORD",
                message="Password cannot exceed 128 characters.",
            )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """Executes PDF decryption pipeline to remove password protection."""
        # 1. Validate input file
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Unlock PDF requires exactly 1 input file.",
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

        # 3. Read input PDF
        try:
            reader = pypdf.PdfReader(local_path)
        except (PdfReadError, PdfStreamError, PyPdfError, Exception) as e:
            raise AppException(
                status_code=400,
                code="CORRUPTED_FILE",
                message=f"File '{original_name}' is corrupted or not a valid PDF: {str(e)}",
            )

        # Verify that the PDF is actually encrypted
        if not reader.is_encrypted:
            raise AppException(
                status_code=400,
                code="NOT_ENCRYPTED",
                message=f"File '{original_name}' is not password-protected and does not need to be unlocked.",
            )

        # 4. Attempt decryption with supplied password
        try:
            decrypt_result = reader.decrypt(password)
        except Exception as e:
            raise AppException(
                status_code=400,
                code="DECRYPTION_FAILED",
                message=f"Failed to decrypt file '{original_name}': {str(e)}",
            )

        # 0 means PasswordType.NOT_DECRYPTED
        if decrypt_result == 0:
            raise AppException(
                status_code=400,
                code="INCORRECT_PASSWORD",
                message="The password provided is incorrect.",
            )

        try:
            total_pages = len(reader.pages)
        except Exception as e:
            raise AppException(
                status_code=400,
                code="CORRUPTED_FILE",
                message=f"Failed to read decrypted pages for '{original_name}': {str(e)}",
            )

        if total_pages == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_DOCUMENT",
                message=f"File '{original_name}' has 0 pages and cannot be processed.",
            )

        if context.progress_callback:
            await context.progress_callback(40)

        # 5. Construct unencrypted output PDF
        writer = pypdf.PdfWriter()
        for idx, page in enumerate(reader.pages):
            writer.add_page(page)
            if context.progress_callback and idx % 5 == 0:
                pct = 40 + int((idx / total_pages) * 45)
                await context.progress_callback(pct)

        if reader.metadata:
            try:
                writer.add_metadata(reader.metadata)
            except Exception:
                pass

        # 6. Save output file
        custom_name = config.get("output_filename")
        if custom_name and isinstance(custom_name, str) and custom_name.strip():
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
            output_filename = safe_name
        else:
            base_name, _ = os.path.splitext(original_name)
            if base_name.startswith("protected_"):
                base_name = base_name[len("protected_"):]
            output_filename = f"unlocked_{base_name}.pdf"

        output_path = os.path.join(context.temp_dir, f"unlock_{context.job_id}.pdf")

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        # 7. Verification: Ensure output is non-empty and NOT encrypted
        out_size = os.path.getsize(output_path)
        if out_size == 0:
            raise AppException(
                status_code=500,
                code="PROCESSING_ERROR",
                message="Generated unlocked PDF file is empty.",
            )

        try:
            verify_reader = pypdf.PdfReader(output_path)
            if verify_reader.is_encrypted:
                raise AppException(
                    status_code=500,
                    code="DECRYPTION_ERROR",
                    message="Generated PDF is still encrypted.",
                )
        except Exception as e:
            if isinstance(e, AppException):
                raise
            raise AppException(
                status_code=500,
                code="PROCESSING_ERROR",
                message=f"Failed to verify unlocked PDF integrity: {str(e)}",
            )

        sha256 = hashlib.sha256()
        with open(output_path, "rb") as f_out:
            while chunk := f_out.read(65536):
                sha256.update(chunk)

        if context.progress_callback:
            await context.progress_callback(95)

        # Explicitly clear password in memory
        del password
        if "password" in config:
            config["password"] = None

        return {
            "output_path": output_path,
            "local_path": output_path,
            "filename": output_filename,
            "size_bytes": out_size,
            "page_count": total_pages,
            "is_encrypted": False,
            "sha256": sha256.hexdigest(),
            "content_type": "application/pdf",
        }
