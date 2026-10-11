import hashlib
import os
from typing import Dict, Any, List, Union
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


def normalize_organize_pages(
    pages_spec: Union[List[Union[Dict[str, Any], int, str]], str],
    total_pages: int,
) -> List[Dict[str, int]]:
    """
    Normalizes page organization specification into a list of dicts:
    [{"page_number": int, "rotation": int}, ...]

    Accepts:
      - List of dicts: [{"page_number": 1, "rotation": 90}, {"page": 2, "rotation": 0}]
      - List of integers: [2, 1, 3]
      - Comma-separated string: "2, 1, 3"
    """
    if not pages_spec:
        raise AppException(
            status_code=400,
            code="INVALID_CONFIG",
            message="Please specify at least one page to include in the organized PDF.",
        )

    items: List[Any] = []
    if isinstance(pages_spec, str):
        parts = [p.strip() for p in pages_spec.split(",") if p.strip()]
        for p in parts:
            if not p.isdigit():
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_NUMBER",
                    message=f"Invalid page number '{p}'. Expected an integer.",
                )
            items.append(int(p))
    elif isinstance(pages_spec, list):
        items = pages_spec
    else:
        raise AppException(
            status_code=400,
            code="INVALID_CONFIG",
            message="Invalid 'pages' format. Expected list of page items or page numbers.",
        )

    if not items:
        raise AppException(
            status_code=400,
            code="INVALID_CONFIG",
            message="Please specify at least one page to include in the organized PDF.",
        )

    normalized: List[Dict[str, int]] = []
    for idx, item in enumerate(items):
        page_num: int
        rotation: int = 0

        if isinstance(item, int):
            page_num = item
        elif isinstance(item, str):
            if not item.isdigit():
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_NUMBER",
                    message=f"Invalid page number '{item}'. Expected an integer.",
                )
            page_num = int(item)
        elif isinstance(item, dict):
            num = item.get("page_number") or item.get("page")
            if num is None:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Item at index {idx} is missing 'page_number'.",
                )
            if not isinstance(num, int):
                try:
                    num = int(num)
                except (ValueError, TypeError):
                    raise AppException(
                        status_code=400,
                        code="INVALID_PAGE_NUMBER",
                        message=f"Page number at index {idx} must be an integer.",
                    )
            page_num = num

            raw_rot = item.get("rotation", 0)
            try:
                rot_val = int(raw_rot)
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_ROTATION_ANGLE",
                    message=f"Invalid rotation angle '{raw_rot}' at index {idx}. Must be an integer multiple of 90.",
                )
            if rot_val % 90 != 0:
                raise AppException(
                    status_code=400,
                    code="INVALID_ROTATION_ANGLE",
                    message=f"Rotation angle {rot_val}° at index {idx} is invalid. Only multiples of 90° are supported.",
                )
            rotation = rot_val % 360
        else:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message=f"Unexpected item type at index {idx}: {type(item).__name__}",
            )

        if page_num < 1:
            raise AppException(
                status_code=400,
                code="PAGE_RANGE_OUT_OF_BOUNDS",
                message=f"Page number must be 1 or greater: {page_num}.",
            )
        if page_num > total_pages:
            raise AppException(
                status_code=400,
                code="PAGE_RANGE_OUT_OF_BOUNDS",
                message=f"Page {page_num} is out of bounds for a document with {total_pages} pages.",
            )

        normalized.append({"page_number": page_num, "rotation": rotation})

    return normalized


class OrganizePDFHandler(ToolHandler):
    """
    Handler for organizing a PDF document.
    Supports:
      - Reordering pages arbitrarily
      - Deleting pages (omitting from output)
      - Duplicating pages (referencing same source page multiple times)
      - Rotating individual pages in 90° increments
    Preserves page content, dimensions, original orientation, and metadata.
    Uses pypdf (BSD-3-Clause).
    """

    tool_id = "organize_pdf"
    display_name = "Organize PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates organize configuration before worker processing."""
        if not config:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Organize PDF configuration is required.",
            )

        pages = config.get("pages") or config.get("page_order")
        if not pages:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Please specify pages to include in the organized PDF.",
            )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """Executes the organize PDF pipeline."""
        # 1. Validate input file
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Organize PDF requires exactly 1 input file.",
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

        # 2. Validate configuration
        config = context.config or {}
        self.validate_config(config)

        pages_spec = config.get("pages") or config.get("page_order")

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
            await context.progress_callback(15)

        # 4. Normalize and validate pages spec against actual total_pages
        target_pages = normalize_organize_pages(pages_spec, total_pages)

        # 5. Build output PDF
        writer = pypdf.PdfWriter()
        total_items = len(target_pages)

        for i, item in enumerate(target_pages):
            src_page_idx = item["page_number"] - 1
            src_page = reader.pages[src_page_idx]

            writer.add_page(src_page)
            rot = item.get("rotation", 0) % 360
            if rot != 0:
                writer.pages[-1].rotate(rot)

            if context.progress_callback and i % 5 == 0:
                pct = 20 + int((i / total_items) * 65)
                await context.progress_callback(pct)

        # 6. Preserve document metadata if present
        if reader.metadata:
            try:
                writer.add_metadata(reader.metadata)
            except Exception:
                pass

        if context.progress_callback:
            await context.progress_callback(85)

        # 7. Write output
        custom_name = config.get("output_filename")
        if custom_name and isinstance(custom_name, str) and custom_name.strip():
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
            output_filename = safe_name
        else:
            base_name, _ = os.path.splitext(original_name)
            output_filename = f"organized_{base_name}.pdf"

        output_path = os.path.join(context.temp_dir, f"organized_{context.job_id}.pdf")

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
            "page_count": total_items,
            "sha256": sha256.hexdigest(),
            "content_type": "application/pdf",
        }
