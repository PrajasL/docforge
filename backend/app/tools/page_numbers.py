import hashlib
import io
import os
import re
from typing import Dict, Any, Tuple
import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


def parse_hex_color(hex_str: str) -> Tuple[float, float, float]:
    """Parses a hex color string (e.g. '#000000', '#374151') into RGB float tuple (0.0 to 1.0)."""
    if not hex_str:
        return (0.2, 0.2, 0.2)
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6 or not re.match(r"^[0-9a-fA-F]{6}$", clean):
        return (0.2, 0.2, 0.2)
    try:
        r = int(clean[0:2], 16) / 255.0
        g = int(clean[2:4], 16) / 255.0
        b = int(clean[4:6], 16) / 255.0
        return (r, g, b)
    except Exception:
        return (0.2, 0.2, 0.2)


class PageNumbersPDFHandler(ToolHandler):
    """
    Handler for stamping page numbers onto PDF documents.
    Supports flexible positions (top/bottom, left/center/right), starting page,
    starting number, font size, color, and diverse numbering formats.
    """

    tool_id = "page_numbers"
    display_name = "Add Page Numbers"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    VALID_POSITIONS = {
        "bottom_center",
        "bottom_right",
        "bottom_left",
        "top_center",
        "top_right",
        "top_left",
    }
    VALID_FORMATS = {"n", "page_n", "page_n_of_total", "n_of_total"}

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates page numbering configuration."""
        if not config:
            return

        # 1. Position validation
        if "position" in config:
            pos = str(config.get("position", "")).lower()
            if pos not in self.VALID_POSITIONS:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Invalid position '{pos}'. Must be one of: {', '.join(sorted(self.VALID_POSITIONS))}.",
                )

        # 2. Format validation
        if "format" in config:
            fmt = str(config.get("format", "")).lower()
            if fmt not in self.VALID_FORMATS:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Invalid format '{fmt}'. Must be one of: {', '.join(sorted(self.VALID_FORMATS))}.",
                )

        # 3. Start number validation
        if "start_number" in config:
            try:
                sn = int(config.get("start_number"))
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'start_number' must be an integer.",
                )
            if sn < 1:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'start_number' must be >= 1.",
                )

        # 4. Start page validation
        if "start_page" in config:
            try:
                sp = int(config.get("start_page"))
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'start_page' must be an integer.",
                )
            if sp < 1:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'start_page' must be >= 1.",
                )

        # 5. End page validation
        if "end_page" in config and config.get("end_page") is not None:
            try:
                ep = int(config.get("end_page"))
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'end_page' must be an integer.",
                )
            start_p = int(config.get("start_page", 1))
            if ep < start_p:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Parameter 'end_page' ({ep}) cannot be less than 'start_page' ({start_p}).",
                )

        # 6. Font size validation
        if "font_size" in config:
            try:
                fs = int(config.get("font_size"))
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'font_size' must be an integer.",
                )
            if not (8 <= fs <= 36):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Parameter 'font_size' must be between 8 and 36. Received: {fs}.",
                )

        # 7. Margin validation
        if "margin" in config:
            try:
                mg = float(config.get("margin"))
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Parameter 'margin' must be a number.",
                )
            if not (10 <= mg <= 100):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Parameter 'margin' must be between 10 and 100 pt. Received: {mg}.",
                )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """Executes page numbering pipeline."""
        # 1. Validate input file
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Add Page Numbers requires exactly 1 input file.",
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

        # 2. Extract configuration
        config = context.config or {}
        self.validate_config(config)

        position = str(config.get("position", "bottom_center")).lower()
        num_format = str(config.get("format", "page_n_of_total")).lower()
        start_number = int(config.get("start_number", 1))
        start_page = int(config.get("start_page", 1))
        end_page = int(config.get("end_page")) if config.get("end_page") is not None else None
        font_size = int(config.get("font_size", 12))
        margin = float(config.get("margin", 36))
        color_str = str(config.get("color", "#374151"))
        r, g, b = parse_hex_color(color_str)

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
            try:
                decrypted = reader.decrypt("")
                if not decrypted:
                    raise AppException(
                        status_code=400,
                        code="DOCUMENT_ENCRYPTED",
                        message=f"File '{original_name}' is password-protected and cannot be processed.",
                    )
            except Exception:
                raise AppException(
                    status_code=400,
                    code="DOCUMENT_ENCRYPTED",
                    message=f"File '{original_name}' is password-protected and cannot be processed.",
                )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_DOCUMENT",
                message=f"File '{original_name}' has 0 pages and cannot be processed.",
            )

        if start_page > total_pages:
            raise AppException(
                status_code=400,
                code="PAGE_NUMBER_OUT_OF_BOUNDS",
                message=f"Start page {start_page} exceeds document total page count ({total_pages}).",
            )

        final_end_page = min(end_page, total_pages) if end_page else total_pages
        effective_numbered_count = max(0, final_end_page - start_page + 1)
        counted_total = start_number + effective_numbered_count - 1

        # 4. Stamp page numbers
        writer = pypdf.PdfWriter()
        numbered_pages_count = 0

        for idx, page in enumerate(reader.pages):
            page_num_1indexed = idx + 1

            # Normalize rotation so visual orientation is upright
            if page.get("/Rotate", 0) != 0:
                page.transfer_rotation_to_content()

            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            if start_page <= page_num_1indexed <= final_end_page:
                current_num = start_number + (page_num_1indexed - start_page)
                numbered_pages_count += 1

                # Format label
                if num_format == "n":
                    label = f"{current_num}"
                elif num_format == "page_n":
                    label = f"Page {current_num}"
                elif num_format == "n_of_total":
                    label = f"{current_num} of {counted_total}"
                else:  # "page_n_of_total"
                    label = f"Page {current_num} of {counted_total}"

                # Calculate coordinates and alignment
                if position.startswith("top"):
                    y = height - margin
                else:
                    y = margin

                if position.endswith("left"):
                    x = margin
                    align = "left"
                elif position.endswith("right"):
                    x = width - margin
                    align = "right"
                else:  # "center"
                    x = width / 2.0
                    align = "center"

                # Generate canvas overlay
                overlay_io = io.BytesIO()
                canv = canvas.Canvas(overlay_io, pagesize=(width, height))
                canv.setFillColor(colors.Color(r, g, b, alpha=1.0))
                canv.setFont("Helvetica", font_size)

                if align == "center":
                    canv.drawCentredString(x, y, label)
                elif align == "right":
                    canv.drawRightString(x, y, label)
                else:
                    canv.drawString(x, y, label)

                canv.save()
                overlay_io.seek(0)

                overlay_reader = pypdf.PdfReader(overlay_io)
                page.merge_page(overlay_reader.pages[0], over=True)

            writer.add_page(page)

        # 5. Save output file
        custom_name = config.get("output_filename")
        if custom_name and isinstance(custom_name, str) and custom_name.strip():
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
            output_filename = safe_name
        else:
            base_name, _ = os.path.splitext(original_name)
            output_filename = f"numbered_{base_name}.pdf"

        output_path = os.path.join(context.temp_dir, f"pagenumbers_{context.job_id}.pdf")

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

        out_size = os.path.getsize(output_path)
        sha256 = hashlib.sha256()
        with open(output_path, "rb") as f_out:
            while chunk := f_out.read(65536):
                sha256.update(chunk)

        return {
            "output_path": output_path,
            "local_path": output_path,
            "filename": output_filename,
            "size_bytes": out_size,
            "page_count": total_pages,
            "numbered_pages_count": numbered_pages_count,
            "numbering_format": num_format,
            "position": position,
            "sha256": sha256.hexdigest(),
            "content_type": "application/pdf",
        }
