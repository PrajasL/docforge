import hashlib
import io
import os
from typing import Dict, Any, List, Set, Union
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError

from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


def parse_page_selection(pages_spec: Union[str, List[int], None], total_pages: int) -> Set[int]:
    """
    Parses a page selection specification into a set of 0-indexed page indices.
    Examples of pages_spec:
      - None or "all" -> all pages
      - "1, 3, 5-7"   -> pages 1, 3, 5, 6, 7
      - [1, 3]        -> pages 1, 3
    """
    if pages_spec is None or pages_spec == "" or pages_spec == "all":
        return set(range(total_pages))

    if isinstance(pages_spec, list):
        selected = set()
        for p in pages_spec:
            if not isinstance(p, int):
                raise AppException(
                    status_code=400,
                    code="INVALID_PAGE_NUMBER",
                    message=f"Page numbers must be integers. Received: {p}",
                )
            if p < 1 or p > total_pages:
                raise AppException(
                    status_code=400,
                    code="PAGE_NUMBER_OUT_OF_BOUNDS",
                    message=f"Page number {p} is out of bounds (document has {total_pages} pages).",
                )
            selected.add(p - 1)
        return selected

    if isinstance(pages_spec, str):
        selected = set()
        parts = [p.strip() for p in pages_spec.split(",") if p.strip()]
        if not parts:
            return set(range(total_pages))

        for part in parts:
            if "-" in part:
                segments = [s.strip() for s in part.split("-")]
                if len(segments) != 2 or not segments[0].isdigit() or not segments[1].isdigit():
                    raise AppException(
                        status_code=400,
                        code="INVALID_PAGE_RANGE",
                        message=f"Invalid page range syntax: '{part}'. Use 'start-end' (e.g. '1-3').",
                    )
                start = int(segments[0])
                end = int(segments[1])

                if start < 1:
                    raise AppException(
                        status_code=400,
                        code="PAGE_NUMBER_OUT_OF_BOUNDS",
                        message=f"Page numbers must start at 1 or greater: '{part}'.",
                    )
                if start > end:
                    raise AppException(
                        status_code=400,
                        code="INVALID_PAGE_RANGE",
                        message=f"Start page {start} cannot exceed end page {end}.",
                    )
                if end > total_pages:
                    raise AppException(
                        status_code=400,
                        code="PAGE_NUMBER_OUT_OF_BOUNDS",
                        message=f"Range '{part}' exceeds total pages in document ({total_pages}).",
                    )
                for p_num in range(start, end + 1):
                    selected.add(p_num - 1)
            else:
                if not part.isdigit():
                    raise AppException(
                        status_code=400,
                        code="INVALID_PAGE_NUMBER",
                        message=f"Page number must be a positive integer: '{part}'.",
                    )
                p_num = int(part)
                if p_num < 1 or p_num > total_pages:
                    raise AppException(
                        status_code=400,
                        code="PAGE_NUMBER_OUT_OF_BOUNDS",
                        message=f"Page number {p_num} is out of bounds (document has {total_pages} pages).",
                    )
                selected.add(p_num - 1)

        return selected

    raise AppException(
        status_code=400,
        code="INVALID_CONFIG",
        message="Invalid 'pages' specification. Must be 'all', a list, or comma-separated string.",
    )


class RotatePDFHandler(ToolHandler):
    """
    Handler for rotating pages in a PDF document.
    Supports rotating all pages or selectively rotating specific pages by 90°, 180°, or 270°.
    """

    tool_id = "rotate"
    display_name = "Rotate PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates rotation angle and page settings."""
        if not config:
            return

        if "page_rotations" in config:
            page_rotations = config.get("page_rotations")
            if not isinstance(page_rotations, dict):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="'page_rotations' must be an object mapping page numbers to rotation angles.",
                )
            for page_k, rot in page_rotations.items():
                if not str(page_k).isdigit() or int(page_k) < 1:
                    raise AppException(
                        status_code=400,
                        code="INVALID_PAGE_NUMBER",
                        message=f"Invalid page key '{page_k}'. Must be a 1-indexed page number.",
                    )
                try:
                    rot_int = int(rot) % 360
                except (ValueError, TypeError):
                    raise AppException(
                        status_code=400,
                        code="INVALID_ROTATION_ANGLE",
                        message=f"Invalid rotation angle '{rot}' for page {page_k}.",
                    )
                if rot_int not in (90, 180, 270):
                    raise AppException(
                        status_code=400,
                        code="INVALID_ROTATION_ANGLE",
                        message=f"Rotation angle for page {page_k} must be 90, 180, or 270 degrees.",
                    )
        else:
            angle = config.get("angle", 90)
            try:
                angle_int = int(angle) % 360
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_ROTATION_ANGLE",
                    message=f"Rotation angle must be an integer (e.g. 90, 180, 270). Received: '{angle}'.",
                )
            if angle_int not in (90, 180, 270):
                raise AppException(
                    status_code=400,
                    code="INVALID_ROTATION_ANGLE",
                    message=f"Rotation angle must be 90, 180, or 270 degrees. Received: {angle}°.",
                )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """Executes PDF rotation pipeline."""
        # 1. Validate file count
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Rotate PDF requires exactly 1 input file.",
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

        file_size = os.path.getsize(local_path)
        if file_size == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_FILE",
                message=f"File '{original_name}' is empty (0 bytes).",
            )

        # 2. Read input PDF
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
                    message=f"File '{original_name}' is password-protected and cannot be rotated.",
                )

            total_pages = len(reader.pages)
            if total_pages == 0:
                raise AppException(
                    status_code=400,
                    code="EMPTY_PDF",
                    message=f"File '{original_name}' contains no readable pages.",
                )

            # 3. Determine rotation per page
            # Mapping of 0-indexed page index -> rotation angle in degrees
            rotations_to_apply: Dict[int, int] = {}

            if "page_rotations" in context.config:
                raw_mapping = context.config["page_rotations"]
                for p_str, r_val in raw_mapping.items():
                    p_num = int(p_str)
                    if p_num < 1 or p_num > total_pages:
                        raise AppException(
                            status_code=400,
                            code="PAGE_NUMBER_OUT_OF_BOUNDS",
                            message=f"Page number {p_num} is out of bounds (document has {total_pages} pages).",
                        )
                    rotations_to_apply[p_num - 1] = int(r_val) % 360
            else:
                raw_angle = context.config.get("angle", 90)
                try:
                    norm_angle = int(raw_angle) % 360
                except (ValueError, TypeError):
                    raise AppException(
                        status_code=400,
                        code="INVALID_ROTATION_ANGLE",
                        message=f"Invalid rotation angle: '{raw_angle}'.",
                    )
                if norm_angle not in (90, 180, 270):
                    raise AppException(
                        status_code=400,
                        code="INVALID_ROTATION_ANGLE",
                        message=f"Rotation angle must be 90, 180, or 270 degrees. Received: {raw_angle}°.",
                    )

                pages_spec = context.config.get("pages", "all")
                selected_indices = parse_page_selection(pages_spec, total_pages)
                for idx in selected_indices:
                    rotations_to_apply[idx] = norm_angle

            # 4. Construct rotated PDF
            writer = pypdf.PdfWriter()

            for idx, page in enumerate(reader.pages):
                if idx in rotations_to_apply:
                    rot = rotations_to_apply[idx]
                    page.rotate(rot)
                writer.add_page(page)

                # Report progress (from 20% to 80%)
                progress = 20 + int(60 * (idx + 1) / total_pages)
                if context.progress_callback:
                    res = context.progress_callback(progress)
                    if hasattr(res, "__await__"):
                        await res

            # 5. Write rotated output PDF
            output_filename = context.config.get("output_filename") or f"rotated_{original_name}"
            if not output_filename.lower().endswith(".pdf"):
                output_filename += ".pdf"

            output_path = os.path.join(context.temp_dir, "output.pdf")
            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            out_size = os.path.getsize(output_path)

            sha256 = hashlib.sha256()
            with open(output_path, "rb") as f_out:
                while chunk := f_out.read(65536):
                    sha256.update(chunk)
            sha256_hash = sha256.hexdigest()
            rotation_angle_result = norm_angle if "page_rotations" not in context.config else None

            return {
                "output_path": output_path,
                "filename": output_filename,
                "size_bytes": out_size,
                "page_count": total_pages,
                "rotation_angle": rotation_angle_result,
                "rotated_pages_count": len(rotations_to_apply),
                "content_type": "application/pdf",
                "sha256": sha256_hash,
            }

        finally:
            if f_handle:
                try:
                    f_handle.close()
                except Exception:
                    pass
