import hashlib
import os
import re
from typing import Dict, Any, List, Union
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


def parse_extract_pages(
    pages_spec: Union[str, List[Union[str, int]]], total_pages: int, extract_all: bool = False
) -> List[int]:
    """
    Parses page specification into a 0-indexed list of page indices to extract,
    preserving the exact order specified by the user.

    Supports:
      - extract_all=True or pages_spec="all" -> all pages in order [0, 1, ..., total_pages - 1]
      - Single page numbers: "1, 3, 8" -> [0, 2, 7]
      - Page ranges: "3-5" -> [2, 3, 4]
      - Mixed combinations: "1, 3-5, 8" -> [0, 2, 3, 4, 7]
      - Custom non-sequential order: "5, 2-3, 1" -> [4, 1, 2, 0]
      - Overlapping/duplicate ranges: "2, 2-3" -> [1, 1, 2]
    """
    if extract_all or (isinstance(pages_spec, str) and pages_spec.strip().lower() == "all"):
        return list(range(total_pages))

    raw_parts: List[str] = []
    if isinstance(pages_spec, str):
        raw_parts = [p.strip() for p in pages_spec.split(",") if p.strip()]
    elif isinstance(pages_spec, list):
        for item in pages_spec:
            if isinstance(item, (int, str)):
                for sub in str(item).split(","):
                    if sub.strip():
                        raw_parts.append(sub.strip())

    if not raw_parts:
        raise AppException(
            status_code=400,
            code="INVALID_PAGE_RANGE",
            message="Please specify at least one valid page number or range to extract (e.g. '1, 3-5, 8').",
        )

    extracted_indices: List[int] = []

    for part in raw_parts:
        if "-" in part:
            segments = [s.strip() for s in part.split("-")]
            if len(segments) != 2:
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message=f"Invalid page range format: '{part}'. Expected 'start-end' (e.g. '3-5').",
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

            extracted_indices.extend(range(start - 1, end))

        else:
            if not part.isdigit():
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_RANGE",
                    message=f"Invalid page number: '{part}'. Expected an integer.",
                )

            page_num = int(part)
            if page_num < 1:
                raise AppException(
                    status_code=400,
                    code="PAGE_RANGE_OUT_OF_BOUNDS",
                    message=f"Page numbers must be 1 or greater: '{part}'.",
                )
            if page_num > total_pages:
                raise AppException(
                    status_code=400,
                    code="PAGE_RANGE_OUT_OF_BOUNDS",
                    message=f"Page {page_num} is out of bounds for a document with {total_pages} pages.",
                )

            extracted_indices.append(page_num - 1)

    if not extracted_indices:
        raise AppException(
            status_code=400,
            code="INVALID_PAGE_RANGE",
            message="No pages were selected for extraction.",
        )

    return extracted_indices


class ExtractPagesPDFHandler(ToolHandler):
    """
    Handler for extracting specific pages or page ranges from a PDF document into a single PDF.
    Preserves document rotation, dimensions, and metadata.
    Uses pypdf (BSD-3-Clause).
    """

    tool_id = "extract_pages"
    display_name = "Extract Pages"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates extract pages configuration before worker execution."""
        if not config:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Extract pages configuration is required.",
            )

        extract_all = config.get("extract_all", False)
        pages_spec = config.get("pages") or config.get("page_range") or config.get("ranges")

        if not extract_all and not pages_spec:
            raise AppException(
                status_code=400,
                code="INVALID_PAGE_RANGE",
                message="Please specify pages to extract (e.g. '1, 3-5, 8') or enable 'extract_all'.",
            )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """Executes page extraction pipeline into a single PDF."""
        # 1. Validate input file
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Extract Pages requires exactly 1 input file.",
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

        extract_all = bool(config.get("extract_all", False))
        pages_spec = config.get("pages") or config.get("page_range") or config.get("ranges")

        # 3. Read input PDF
        try:
            reader = pypdf.PdfReader(local_path)
        except (PdfReadError, PdfStreamError, PyPdfError, Exception) as e:
            raise AppException(
                status_code=400,
                code="CORRUPTED_FILE",
                message=f"File '{original_name}' is corrupted or not a valid PDF: {str(e)}",
            )

        if reader.is_encrypted:
            raise AppException(
                status_code=400,
                code="ENCRYPTED_FILE",
                message=f"File '{original_name}' is password-protected and cannot be processed.",
            )

        try:
            total_pages = len(reader.pages)
        except Exception as e:
            raise AppException(
                status_code=400,
                code="CORRUPTED_FILE",
                message=f"Failed to read pages from '{original_name}': {str(e)}",
            )

        if total_pages == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_DOCUMENT",
                message=f"File '{original_name}' has 0 pages and cannot be processed.",
            )

        if context.progress_callback:
            await context.progress_callback(20)

        # 4. Parse requested page indices
        extracted_indices = parse_extract_pages(pages_spec, total_pages, extract_all=extract_all)

        # 5. Extract pages into single PDF writer
        writer = pypdf.PdfWriter()
        total_to_extract = len(extracted_indices)

        for i, page_idx in enumerate(extracted_indices):
            page_obj = reader.pages[page_idx]
            writer.add_page(page_obj)

            if context.progress_callback and i % 5 == 0:
                pct = 20 + int((i / total_to_extract) * 60)
                await context.progress_callback(pct)

        if reader.metadata:
            try:
                writer.add_metadata(reader.metadata)
            except Exception:
                pass

        if context.progress_callback:
            await context.progress_callback(85)

        # 6. Save output file
        custom_name = config.get("output_filename")
        if custom_name and isinstance(custom_name, str) and custom_name.strip():
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
            output_filename = safe_name
        else:
            base_name, _ = os.path.splitext(original_name)
            output_filename = f"extracted_{base_name}.pdf"

        output_path = os.path.join(context.temp_dir, f"extracted_{context.job_id}.pdf")

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        out_size = os.path.getsize(output_path)
        sha256 = hashlib.sha256()
        with open(output_path, "rb") as f_out:
            while chunk := f_out.read(65536):
                sha256.update(chunk)

        if context.progress_callback:
            await context.progress_callback(100)

        return {
            "output_path": output_path,
            "local_path": output_path,
            "filename": output_filename,
            "size_bytes": out_size,
            "page_count": total_to_extract,
            "sha256": sha256.hexdigest(),
            "content_type": "application/pdf",
        }
