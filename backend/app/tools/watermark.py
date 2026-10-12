import hashlib
import io
import math
import os
import re
from typing import Any

import pypdf
from pypdf.errors import PdfReadError, PdfStreamError, PyPdfError
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from app.core.errors import AppException
from app.tools.base import ProcessingContext, ToolHandler
from app.tools.rotate import parse_page_selection


def parse_hex_color(hex_str: str) -> tuple[float, float, float]:
    """Parses a hex color string (e.g. '#000000', '#FF0000', '666') into RGB float tuple (0.0 to 1.0)."""
    if not hex_str:
        return (0.0, 0.0, 0.0)
    clean = hex_str.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6 or not re.match(r"^[0-9a-fA-F]{6}$", clean):
        return (0.0, 0.0, 0.0)
    try:
        r = int(clean[0:2], 16) / 255.0
        g = int(clean[2:4], 16) / 255.0
        b = int(clean[4:6], 16) / 255.0
        return (r, g, b)
    except Exception:
        return (0.0, 0.0, 0.0)


class WatermarkPDFHandler(ToolHandler):
    """
    Handler for applying text watermarks to PDF documents.
    Supports customizable text, font size, opacity, rotation angle, position,
    and applying to all pages or selected page ranges.
    """

    tool_id = "watermark"
    display_name = "Watermark PDF"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validates watermark configuration."""
        if not config:
            return

        # 1. Text validation
        if "text" in config:
            text = config.get("text")
            if not isinstance(text, str):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Watermark 'text' must be a string.",
                )
            if not text.strip():
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Watermark 'text' cannot be empty or blank.",
                )
            if len(text) > 200:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Watermark 'text' cannot exceed 200 characters.",
                )

        # 2. Opacity validation
        if "opacity" in config:
            opacity = config.get("opacity")
            try:
                op_val = float(opacity)
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Watermark 'opacity' must be a number between 0.05 and 1.0. Received: '{opacity}'.",
                )
            if not (0.05 <= op_val <= 1.0):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Watermark 'opacity' must be between 0.05 and 1.0. Received: {op_val}.",
                )

        # 3. Font size validation
        if "font_size" in config:
            font_size = config.get("font_size")
            try:
                fs_val = int(font_size)
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Watermark 'font_size' must be an integer between 8 and 144. Received: '{font_size}'.",
                )
            if not (8 <= fs_val <= 144):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Watermark 'font_size' must be between 8 and 144. Received: {fs_val}.",
                )

        # 4. Position validation
        if "position" in config:
            pos = config.get("position")
            valid_positions = {"center", "diagonal", "top", "bottom"}
            if pos not in valid_positions:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Invalid watermark 'position' '{pos}'. Must be one of: {', '.join(sorted(valid_positions))}.",
                )

        # 5. Angle validation
        if "angle" in config:
            angle = config.get("angle")
            try:
                angle_val = float(angle)
            except (ValueError, TypeError):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Watermark 'angle' must be a number. Received: '{angle}'.",
                )
            if not (-360.0 <= angle_val <= 360.0):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message=f"Watermark 'angle' must be between -360 and 360 degrees. Received: {angle_val}.",
                )

    async def process(self, context: ProcessingContext) -> dict[str, Any]:
        """Executes watermark embedding pipeline."""
        # 1. Validate input file count
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Watermark PDF requires exactly 1 input file.",
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

        text = (config.get("text") or "CONFIDENTIAL").strip()
        opacity = float(config.get("opacity", 0.3))
        font_size = int(config.get("font_size", 48))
        position = str(config.get("position", "diagonal")).lower()
        angle_param = config.get("angle")
        color_str = str(config.get("color", "#000000"))
        r, g, b = parse_hex_color(color_str)
        pages_spec = config.get("pages", "all")

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
                        message=f"File '{original_name}' is password-protected and cannot be watermarked.",
                    )
            except Exception:
                raise AppException(
                    status_code=400,
                    code="DOCUMENT_ENCRYPTED",
                    message=f"File '{original_name}' is password-protected and cannot be watermarked.",
                )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_DOCUMENT",
                message=f"File '{original_name}' has 0 pages and cannot be watermarked.",
            )

        # 4. Determine pages to watermark
        selected_indices = parse_page_selection(pages_spec, total_pages)

        # 5. Build output document
        writer = pypdf.PdfWriter()

        for idx, page in enumerate(reader.pages):
            if idx in selected_indices:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)

                # Determine x, y position and rotation angle
                if position == "diagonal":
                    x = width / 2.0
                    y = height / 2.0
                    if angle_param is not None:
                        calc_angle = float(angle_param)
                    else:
                        calc_angle = math.degrees(math.atan2(height, width))
                elif position == "top":
                    x = width / 2.0
                    y = height * 0.85
                    calc_angle = float(angle_param) if angle_param is not None else 0.0
                elif position == "bottom":
                    x = width / 2.0
                    y = height * 0.15
                    calc_angle = float(angle_param) if angle_param is not None else 0.0
                else:  # "center"
                    x = width / 2.0
                    y = height / 2.0
                    calc_angle = float(angle_param) if angle_param is not None else 0.0

                # Generate in-memory watermark overlay canvas with exact page dimensions
                overlay_io = io.BytesIO()
                canv = canvas.Canvas(overlay_io, pagesize=(width, height))
                canv.setFillColor(colors.Color(r, g, b, alpha=opacity))
                canv.setStrokeColor(colors.Color(r, g, b, alpha=opacity))
                canv.saveState()
                canv.translate(x, y)
                canv.rotate(calc_angle)
                canv.setFont("Helvetica-Bold", font_size)
                canv.drawCentredString(0, -font_size / 3.0, text)
                canv.restoreState()
                canv.save()
                overlay_io.seek(0)

                wm_reader = pypdf.PdfReader(overlay_io)
                page.merge_page(wm_reader.pages[0], over=True)

            writer.add_page(page)

        # 6. Save output file
        custom_name = config.get("output_filename")
        if custom_name and isinstance(custom_name, str) and custom_name.strip():
            safe_name = custom_name.strip()
            if not safe_name.lower().endswith(".pdf"):
                safe_name += ".pdf"
            output_filename = safe_name
        else:
            base_name, _ = os.path.splitext(original_name)
            output_filename = f"watermarked_{base_name}.pdf"

        output_path = os.path.join(context.temp_dir, f"watermark_{context.job_id}.pdf")

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
            "watermarked_pages_count": len(selected_indices),
            "watermark_text": text,
            "sha256": sha256.hexdigest(),
            "content_type": "application/pdf",
        }
