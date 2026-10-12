import hashlib
import io
import os
import zipfile
from typing import Any

import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ProcessingContext, ToolHandler


def parse_page_ranges(
    ranges_spec: str | list[str], total_pages: int
) -> list[tuple[str, list[int]]]:
    """
    Parses range specifications into a list of (output_filename, [0-indexed page indices]).
    Examples of ranges_spec:
      - "1-3, 4-6, 7-9"
      - ["1-3", "4-6"]
      - "1, 3, 5-7"
    """
    raw_parts: list[str] = []
    if isinstance(ranges_spec, str):
        raw_parts = [p.strip() for p in ranges_spec.split(",") if p.strip()]
    elif isinstance(ranges_spec, list):
        for item in ranges_spec:
            if isinstance(item, str):
                for sub in item.split(","):
                    if sub.strip():
                        raw_parts.append(sub.strip())

    if not raw_parts:
        raise AppException(
            status_code=400,
            code="INVALID_PAGE_RANGE",
            message="Please specify at least one valid page range.",
        )

    parsed_groups: list[tuple[str, list[int]]] = []

    for part in raw_parts:
        if "-" in part:
            segments = [s.strip() for s in part.split("-")]
            if len(segments) != 2:
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message=f"Invalid page range syntax: '{part}'. Use 'start-end' (e.g. '1-3').",
                )
            if not segments[0].isdigit() or not segments[1].isdigit():
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message=f"Page numbers must be positive integers: '{part}'.",
                )

            start = int(segments[0])
            end = int(segments[1])

            if start < 1:
                raise AppException(
                    status_code=400,
                    code="PAGE_RANGE_OUT_OF_BOUNDS",
                    message=f"Page numbers must start at 1 or greater: '{part}'.",
                )
            if start > end:
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message=f"Start page ({start}) cannot be greater than end page ({end}) in '{part}'.",
                )
            if end > total_pages:
                raise AppException(
                    status_code=400,
                    code="PAGE_RANGE_OUT_OF_BOUNDS",
                    message=f"Page range '{part}' exceeds the document's total page count ({total_pages}).",
                )

            page_indices = list(range(start - 1, end))
            filename = f"range_{start}-{end}.pdf"
            parsed_groups.append((filename, page_indices))

        else:
            if not part.isdigit():
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message=f"Invalid page number: '{part}'. Must be an integer.",
                )

            page_num = int(part)
            if page_num < 1 or page_num > total_pages:
                raise AppException(
                    status_code=400,
                    code="PAGE_RANGE_OUT_OF_BOUNDS",
                    message=f"Page {page_num} is out of bounds for a document with {total_pages} pages.",
                )

            parsed_groups.append((f"page_{page_num}.pdf", [page_num - 1]))

    return parsed_groups


class SplitPDFHandler(ToolHandler):
    """
    Handler for splitting PDF documents into custom page ranges or separate individual pages.
    Packages extracted PDFs into a ZIP archive.
    Uses pypdf (BSD-3 licensed).
    """

    tool_id = "split"
    display_name = "Split PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validates split mode configuration."""
        if not config:
            return

        mode = config.get("mode", "ranges")
        if mode not in ("ranges", "every_page"):
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message=f"Invalid split mode '{mode}'. Supported modes are 'ranges' and 'every_page'.",
            )

        if mode == "ranges" and "ranges" in config:
            ranges = config.get("ranges")
            if not ranges:
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message="Please specify at least one page range.",
                )

    async def process(self, context: ProcessingContext) -> dict[str, Any]:
        """Processes and splits the input PDF document."""
        # 1. Validate input file count
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Split PDF requires exactly 1 input file.",
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

        # Check empty file (0 bytes)
        file_size = os.path.getsize(local_path)
        if file_size == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_FILE",
                message=f"File '{original_name}' is empty (0 bytes).",
            )

        # 2. Read and validate PDF
        f_handle = None
        try:
            f_handle = open(local_path, "rb")
            reader = pypdf.PdfReader(f_handle)
        except (PdfReadError, PdfStreamError, PyPdfError, Exception) as e:
            if f_handle:
                f_handle.close()
            raise AppException(
                status_code=400,
                code="CORRUPTED_PDF",
                message=f"File '{original_name}' is corrupted or not a valid PDF: {str(e)}",
            )

        try:
            # Check encryption
            if reader.is_encrypted:
                raise AppException(
                    status_code=400,
                    code="PDF_ENCRYPTED",
                    message=f"File '{original_name}' is password-protected and cannot be split.",
                )

            total_pages = len(reader.pages)
            if total_pages == 0:
                raise AppException(
                    status_code=400,
                    code="EMPTY_PDF",
                    message=f"File '{original_name}' contains no readable pages.",
                )

            # 3. Determine split groups based on mode
            mode = context.config.get("mode", "ranges")
            split_groups: list[tuple[str, list[int]]] = []

            if mode == "every_page":
                pad_width = max(len(str(total_pages)), 2)
                for i in range(total_pages):
                    filename = f"page_{i + 1:0{pad_width}d}.pdf"
                    split_groups.append((filename, [i]))
            else:
                ranges_spec = context.config.get("ranges")
                if not ranges_spec:
                    raise AppException(
                        status_code=400,
                        code="INVALID_PAGE_RANGE",
                        message="Please specify page ranges to split.",
                    )
                split_groups = parse_page_ranges(ranges_spec, total_pages)

            # 4. Generate output PDF parts and package into ZIP archive
            output_filename = context.config.get("output_filename") or "split_documents.zip"
            if not output_filename.lower().endswith(".zip"):
                output_filename += ".zip"

            output_path = os.path.join(context.temp_dir, "output.zip")
            total_groups = len(split_groups)

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
                for idx, (part_name, page_indices) in enumerate(split_groups):
                    writer = pypdf.PdfWriter()
                    for p_idx in page_indices:
                        writer.add_page(reader.pages[p_idx])

                    pdf_buffer = io.BytesIO()
                    writer.write(pdf_buffer)
                    writer.close()

                    zip_out.writestr(part_name, pdf_buffer.getvalue())

                    # Report intermediate progress (from 20% to 85%)
                    progress = 20 + int(65 * (idx + 1) / total_groups)
                    if context.progress_callback:
                        res = context.progress_callback(progress)
                        if hasattr(res, "__await__"):
                            await res

            out_size = os.path.getsize(output_path)

            sha256 = hashlib.sha256()
            with open(output_path, "rb") as f_out:
                while chunk := f_out.read(65536):
                    sha256.update(chunk)
            sha256_hash = sha256.hexdigest()

            return {
                "output_path": output_path,
                "filename": output_filename,
                "size_bytes": out_size,
                "content_type": "application/zip",
                "file_count": len(split_groups),
                "sha256": sha256_hash,
            }

        finally:
            if f_handle:
                try:
                    f_handle.close()
                except Exception:
                    pass
