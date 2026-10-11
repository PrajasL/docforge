import hashlib
import os
from typing import Dict, Any, List
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


class MergePDFHandler(ToolHandler):
    """
    Handler for merging multiple PDF documents into a single document.
    Uses pypdf (BSD-3 licensed).
    """

    tool_id = "merge"
    display_name = "Merge PDF"
    min_input_files = 2
    max_input_files = 20
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates optional merge configurations such as custom file ordering."""
        if not config:
            return

        if "file_order" in config:
            file_order = config["file_order"]
            if not isinstance(file_order, list):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="'file_order' must be a list of file IDs.",
                )
            if not all(isinstance(fid, str) for fid in file_order):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="All elements in 'file_order' must be string file IDs.",
                )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """
        Processes and merges input PDF files in the specified order.
        """
        # 1. Validate file count constraints
        if len(context.input_files) < self.min_input_files:
            raise AppException(
                status_code=400,
                code="INSUFFICIENT_FILES",
                message=f"At least {self.min_input_files} PDF files are required to perform a merge.",
            )

        if len(context.input_files) > self.max_input_files:
            raise AppException(
                status_code=400,
                code="TOO_MANY_FILES",
                message=f"A maximum of {self.max_input_files} files can be merged in a single job.",
            )

        # 2. Determine file order
        input_files_map = {f["id"]: f for f in context.input_files}
        ordered_files: List[Dict[str, Any]] = []

        file_order = context.config.get("file_order")
        if file_order:
            self.validate_config(context.config)
            # Reorder according to file_order
            for fid in file_order:
                if fid in input_files_map:
                    ordered_files.append(input_files_map[fid])
            # Append any remaining files not explicitly mentioned
            for f in context.input_files:
                if f not in ordered_files:
                    ordered_files.append(f)
        else:
            ordered_files = list(context.input_files)

        # 3. Open and validate each PDF file
        open_file_handles = []
        readers = []
        total_files = len(ordered_files)

        writer = pypdf.PdfWriter()

        try:
            for idx, file_meta in enumerate(ordered_files):
                local_path = file_meta.get("local_path")
                original_name = file_meta.get("original_name", f"file_{idx + 1}.pdf")

                if not local_path or not os.path.exists(local_path):
                    raise AppException(
                        status_code=404,
                        code="FILE_NOT_FOUND",
                        message=f"Input file '{original_name}' not found on disk.",
                    )

                # Check empty file (0 bytes)
                file_size = os.path.getsize(local_path)
                if file_size == 0:
                    raise AppException(
                        status_code=400,
                        code="EMPTY_FILE",
                        message=f"File '{original_name}' is empty (0 bytes).",
                    )

                try:
                    f_handle = open(local_path, "rb")
                    open_file_handles.append(f_handle)
                    reader = pypdf.PdfReader(f_handle)
                except (PdfReadError, PdfStreamError, PyPdfError, Exception) as e:
                    raise AppException(
                        status_code=400,
                        code="CORRUPTED_PDF",
                        message=f"File '{original_name}' is corrupted or not a valid PDF: {str(e)}",
                    )

                # Check encryption
                if reader.is_encrypted:
                    raise AppException(
                        status_code=400,
                        code="PDF_ENCRYPTED",
                        message=f"File '{original_name}' is password-protected and cannot be merged.",
                    )

                # Check page count
                if len(reader.pages) == 0:
                    raise AppException(
                        status_code=400,
                        code="EMPTY_PDF",
                        message=f"File '{original_name}' contains no readable pages.",
                    )

                readers.append(reader)

                # Append pages to writer
                try:
                    writer.append(reader)
                except Exception as e:
                    raise AppException(
                        status_code=400,
                        code="PDF_MERGE_ERROR",
                        message=f"Failed to append pages from '{original_name}': {str(e)}",
                    )

                # Report intermediate progress (from 20% up to 80%)
                progress = 20 + int(60 * (idx + 1) / total_files)
                if context.progress_callback:
                    res = context.progress_callback(progress)
                    if hasattr(res, "__await__"):
                        await res

            # 4. Write output PDF
            output_filename = context.config.get("output_filename") or "merged_document.pdf"
            if not output_filename.lower().endswith(".pdf"):
                output_filename += ".pdf"

            output_path = os.path.join(context.temp_dir, "output.pdf")
            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            # 5. Calculate metadata
            out_size = os.path.getsize(output_path)
            total_pages = len(writer.pages)

            sha256 = hashlib.sha256()
            with open(output_path, "rb") as f_out:
                while chunk := f_out.read(65536):
                    sha256.update(chunk)
            sha256_hash = sha256.hexdigest()

            return {
                "output_path": output_path,
                "filename": output_filename,
                "size_bytes": out_size,
                "page_count": total_pages,
                "sha256": sha256_hash,
            }

        finally:
            # Ensure all open file handles are closed
            for fh in open_file_handles:
                try:
                    fh.close()
                except Exception:
                    pass
            try:
                writer.close()
            except Exception:
                pass
