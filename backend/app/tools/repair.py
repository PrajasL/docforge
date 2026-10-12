import hashlib
import inspect
import os
from typing import Any

import pikepdf
import pypdf

from app.core.config import settings
from app.core.errors import AppException
from app.core.logging import logger
from app.files.validator import sanitize_filename
from app.tools.base import ProcessingContext, ToolHandler


async def _notify_progress(callback, percent: int) -> None:
    if not callback:
        return
    res = callback(percent)
    if inspect.isawaitable(res):
        await res


class RepairPDFHandler(ToolHandler):
    """
    Handler for repairing damaged or malformed PDF files.
    Safely reconstructs damaged cross-reference (xref) tables, unreferenced stream objects,
    and corrupted trailer dictionaries using QPDF / pikepdf with pypdf fallback.
    Never overwrites original input files; saves recovered content to a new normalized PDF.
    """

    tool_id = "repair"
    display_name = "Repair PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf", "application/x-pdf"]

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validates tool configuration. Repair requires no special config parameters."""
        if not config:
            return
        output_filename = config.get("output_filename")
        if output_filename and not isinstance(output_filename, str):
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="output_filename must be a valid string if provided.",
            )

    async def process(self, context: ProcessingContext) -> dict[str, Any]:
        """
        Executes structural recovery pipeline on the input PDF file.
        1. Validates input existence, size, and boundaries.
        2. Detects password-protection or encryption.
        3. Evaluates structural soundness vs recoverable damage.
        4. Reconstructs xref tables, stream lengths, and trailers into a clean PDF.
        """
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Repair PDF requires exactly 1 input file.",
            )

        file_meta = context.input_files[0]
        local_path = file_meta.get("local_path")
        original_name = file_meta.get("original_name", "document.pdf")

        if not local_path or not os.path.exists(local_path):
            raise AppException(
                status_code=404,
                code="FILE_NOT_FOUND",
                message=f"Input file '{original_name}' not found on disk.",
            )

        input_size = os.path.getsize(local_path)
        if input_size == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_FILE",
                message=f"File '{original_name}' is empty (0 bytes).",
            )

        max_limit_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if input_size > max_limit_bytes:
            raise AppException(
                status_code=413,
                code="FILE_TOO_LARGE",
                message=f"File '{original_name}' exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB.",
            )

        await _notify_progress(context.progress_callback, 15)

        pdf = None
        was_repaired = False
        repair_action = "VERIFIED_SOUND"
        page_count = 0
        used_pypdf_fallback = False
        salvaged_pypdf_writer = None

        # Step 1: Check if document is already structurally sound without recovery
        try:
            pdf = pikepdf.Pdf.open(
                local_path,
                attempt_recovery=False,
                suppress_warnings=True,
            )
            was_repaired = False
            repair_action = "VERIFIED_SOUND"
            page_count = len(pdf.pages)
        except pikepdf.PasswordError:
            raise AppException(
                status_code=400,
                code="PDF_ENCRYPTED",
                message=f"File '{original_name}' is password-protected. Please unlock it using the Unlock PDF tool before repairing.",
            )
        except (pikepdf.PdfError, Exception) as initial_err:
            # Step 2: Document has structural flaws; attempt primary recovery with QPDF / pikepdf
            logger.info(f"PDF '{original_name}' exhibits structural damage ({initial_err}). Initiating recovery...")
            if pdf is not None:
                try:
                    pdf.close()
                except Exception:
                    pass
                pdf = None

            try:
                pdf = pikepdf.Pdf.open(
                    local_path,
                    attempt_recovery=True,
                    suppress_warnings=True,
                )
                was_repaired = True
                repair_action = "XREF_RECONSTRUCTED"
                page_count = len(pdf.pages)
            except pikepdf.PasswordError:
                raise AppException(
                    status_code=400,
                    code="PDF_ENCRYPTED",
                    message=f"File '{original_name}' is password-protected. Please unlock it using the Unlock PDF tool before repairing.",
                )
            except Exception as qpdf_err:
                logger.warning(f"pikepdf recovery failed for '{original_name}': {qpdf_err}. Attempting pypdf fallback...")
                if pdf is not None:
                    try:
                        pdf.close()
                    except Exception:
                        pass
                    pdf = None

                # Step 3: Secondary salvage attempt with pypdf (lenient parsing)
                try:
                    reader = pypdf.PdfReader(local_path, strict=False)
                    if reader.is_encrypted:
                        raise AppException(
                            status_code=400,
                            code="PDF_ENCRYPTED",
                            message=f"File '{original_name}' is password-protected. Please unlock it using the Unlock PDF tool before repairing.",
                        )
                    if len(reader.pages) > 0:
                        salvaged_pypdf_writer = pypdf.PdfWriter()
                        for p in reader.pages:
                            salvaged_pypdf_writer.add_page(p)
                        used_pypdf_fallback = True
                        was_repaired = True
                        repair_action = "SALVAGED_OBJECT_STREAMS"
                        page_count = len(salvaged_pypdf_writer.pages)
                    else:
                        raise AppException(
                            status_code=400,
                            code="UNRECOVERABLE_PDF",
                            message=f"File '{original_name}' is severely corrupted and contains no readable pages.",
                        )
                except AppException:
                    raise
                except Exception as pypdf_err:
                    logger.error(f"Secondary salvage also failed for '{original_name}': {pypdf_err}")
                    raise AppException(
                        status_code=400,
                        code="UNRECOVERABLE_PDF",
                        message=f"File '{original_name}' is severely corrupted and could not be structurally recovered.",
                    )

        await _notify_progress(context.progress_callback, 50)

        # Step 4: Ensure document contains recoverable pages
        if page_count == 0:
            if pdf is not None:
                try:
                    pdf.close()
                except Exception:
                    pass
            raise AppException(
                status_code=400,
                code="EMPTY_DOCUMENT",
                message=f"No valid pages could be recovered from '{original_name}'.",
            )

        # Step 5: Save recovered/normalized PDF to a fresh output file
        base_name, _ = os.path.splitext(original_name)
        config_name = context.config.get("output_filename")
        if config_name and isinstance(config_name, str) and config_name.strip():
            safe_out_name = sanitize_filename(config_name.strip())
        else:
            safe_out_name = sanitize_filename(f"repaired_{base_name}.pdf")

        output_path = os.path.join(context.temp_dir, f"repaired_{context.job_id}.pdf")

        try:
            if used_pypdf_fallback and salvaged_pypdf_writer is not None:
                with open(output_path, "wb") as f_out:
                    salvaged_pypdf_writer.write(f_out)
            elif pdf is not None:
                pdf.save(
                    output_path,
                    linearize=False,
                    fix_metadata_version=True,
                    min_version="1.4",
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                )
        finally:
            if pdf is not None:
                try:
                    pdf.close()
                except Exception:
                    pass

        await _notify_progress(context.progress_callback, 85)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise AppException(
                status_code=500,
                code="PROCESSING_ERROR",
                message="Failed to write repaired PDF to disk.",
            )

        out_size = os.path.getsize(output_path)
        with open(output_path, "rb") as f_sha:
            out_sha256 = hashlib.sha256(f_sha.read()).hexdigest()

        status_detail = (
            f"Successfully reconstructed damaged cross-reference tables and recovered {page_count} page(s)."
            if was_repaired
            else f"Document structure verified and normalized ({page_count} page(s)). No structural damage detected."
        )

        await _notify_progress(context.progress_callback, 95)

        return {
            "output_path": output_path,
            "filename": safe_out_name,
            "size_bytes": out_size,
            "page_count": page_count,
            "repaired": was_repaired,
            "repair_action": repair_action,
            "sha256": out_sha256,
            "status_detail": status_detail,
        }
