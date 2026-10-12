import hashlib
import os
from typing import Any

from PIL import Image, ImageOps
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.core.errors import AppException
from app.tools.base import ProcessingContext, ToolHandler

# Standard page dimensions in points (72 points/inch)
PAGE_SIZES: dict[str, tuple[float, float]] = {
    "a4": (595.27559, 841.88976),
    "letter": (612.0, 792.0),
}

# Margin presets in points
MARGIN_PRESETS: dict[str, float] = {
    "none": 0.0,
    "small": 18.0,   # 0.25 inch
    "normal": 36.0,  # 0.50 inch
}


class JpgToPdfPDFHandler(ToolHandler):
    """
    Converts multiple JPG/JPEG images into a single combined PDF document with custom
    page orientation, page size, margins, and sequence order.
    """

    tool_id = "jpg_to_pdf"
    display_name = "JPG to PDF"
    min_input_files = 1
    max_input_files = 50
    accepted_content_types = ["image/jpeg", "image/jpg"]

    def validate_config(self, config: dict[str, Any]) -> None:
        """
        Validates configuration options for JPG to PDF conversion.
        Supported options:
          - orientation: 'auto' | 'portrait' | 'landscape' (default: 'auto')
          - page_size: 'fit' | 'a4' | 'letter' (default: 'fit')
          - margin: 'none' | 'small' | 'normal' | float/int points (default: 'none')
          - file_order / image_order: List[str] of file IDs or names
          - output_filename: Optional[str]
        """
        if not isinstance(config, dict):
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Config must be a valid dictionary.",
            )

        orientation = config.get("orientation", "auto")
        if not isinstance(orientation, str) or orientation.lower() not in (
            "auto",
            "automatic",
            "portrait",
            "landscape",
        ):
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Orientation must be 'auto', 'portrait', or 'landscape'.",
            )

        page_size = config.get("page_size", "fit")
        if not isinstance(page_size, str) or page_size.lower() not in ("fit", "a4", "letter"):
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Page size must be 'fit', 'a4', or 'letter'.",
            )

        margin = config.get("margin", "none")
        if isinstance(margin, str):
            if margin.lower() not in MARGIN_PRESETS:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Margin preset must be 'none', 'small', or 'normal'.",
                )
        elif isinstance(margin, int | float):
            if margin < 0 or margin > 200:
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="Numeric margin must be between 0 and 200 points.",
                )
        else:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Margin must be 'none', 'small', 'normal', or a numeric point value.",
            )

        file_order = config.get("file_order") or config.get("image_order")
        if file_order is not None:
            if not isinstance(file_order, list) or not all(isinstance(x, str) for x in file_order):
                raise AppException(
                    status_code=400,
                    code="INVALID_CONFIG",
                    message="file_order must be a list of string file identifiers.",
                )

    def _resolve_margin(self, margin_val: Any) -> float:
        if isinstance(margin_val, int | float):
            return float(margin_val)
        if isinstance(margin_val, str):
            return MARGIN_PRESETS.get(margin_val.lower(), 0.0)
        return 0.0

    def _calculate_page_and_draw_rect(
        self,
        img_w: int,
        img_h: int,
        page_size_opt: str,
        orientation_opt: str,
        margin_pt: float,
    ) -> tuple[float, float, float, float, float, float]:
        """
        Computes (page_width, page_height, draw_x, draw_y, draw_width, draw_height) in points.
        """
        page_size_opt = page_size_opt.lower()
        orientation_opt = orientation_opt.lower()

        if page_size_opt == "fit":
            # Page fits the image dimensions directly
            if orientation_opt in ("auto", "automatic"):
                page_w = float(img_w) + 2 * margin_pt
                page_h = float(img_h) + 2 * margin_pt
                draw_w = float(img_w)
                draw_h = float(img_h)
                draw_x = margin_pt
                draw_y = margin_pt
            elif orientation_opt == "portrait":
                if img_w <= img_h:
                    page_w = float(img_w) + 2 * margin_pt
                    page_h = float(img_h) + 2 * margin_pt
                    draw_w = float(img_w)
                    draw_h = float(img_h)
                    draw_x = margin_pt
                    draw_y = margin_pt
                else:
                    # Landscape image requested in portrait page
                    page_w = float(img_h) + 2 * margin_pt
                    page_h = float(img_w) + 2 * margin_pt
                    avail_w = max(1.0, page_w - 2 * margin_pt)
                    avail_h = max(1.0, page_h - 2 * margin_pt)
                    scale = min(avail_w / img_w, avail_h / img_h)
                    draw_w = img_w * scale
                    draw_h = img_h * scale
                    draw_x = margin_pt + (avail_w - draw_w) / 2.0
                    draw_y = margin_pt + (avail_h - draw_h) / 2.0
            else:  # landscape
                if img_w >= img_h:
                    page_w = float(img_w) + 2 * margin_pt
                    page_h = float(img_h) + 2 * margin_pt
                    draw_w = float(img_w)
                    draw_h = float(img_h)
                    draw_x = margin_pt
                    draw_y = margin_pt
                else:
                    # Portrait image requested in landscape page
                    page_w = float(img_h) + 2 * margin_pt
                    page_h = float(img_w) + 2 * margin_pt
                    avail_w = max(1.0, page_w - 2 * margin_pt)
                    avail_h = max(1.0, page_h - 2 * margin_pt)
                    scale = min(avail_w / img_w, avail_h / img_h)
                    draw_w = img_w * scale
                    draw_h = img_h * scale
                    draw_x = margin_pt + (avail_w - draw_w) / 2.0
                    draw_y = margin_pt + (avail_h - draw_h) / 2.0
        else:
            base_dims = PAGE_SIZES.get(page_size_opt, PAGE_SIZES["a4"])
            w_standard, h_standard = min(base_dims), max(base_dims)

            if orientation_opt in ("auto", "automatic"):
                if img_w > img_h:
                    page_w, page_h = h_standard, w_standard  # landscape
                else:
                    page_w, page_h = w_standard, h_standard  # portrait
            elif orientation_opt == "landscape":
                page_w, page_h = h_standard, w_standard
            else:  # portrait
                page_w, page_h = w_standard, h_standard

            avail_w = max(1.0, page_w - 2 * margin_pt)
            avail_h = max(1.0, page_h - 2 * margin_pt)
            scale = min(avail_w / img_w, avail_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
            draw_x = margin_pt + (avail_w - draw_w) / 2.0
            draw_y = margin_pt + (avail_h - draw_h) / 2.0

        return page_w, page_h, draw_x, draw_y, draw_w, draw_h

    async def process(self, context: ProcessingContext) -> dict[str, Any]:
        """
        Converts the ordered input JPEG files into a single combined PDF document.
        Strictly enforces all resource limits and cleans up upon completion or failure.
        """
        max_files_limit = getattr(settings, "JPG_TO_PDF_MAX_FILES", 50)
        if len(context.input_files) < self.min_input_files:
            raise AppException(
                status_code=400,
                code="INSUFFICIENT_FILES",
                message=f"At least {self.min_input_files} image file is required.",
            )

        if len(context.input_files) > max_files_limit:
            raise AppException(
                status_code=400,
                code="TOO_MANY_FILES",
                message=f"A maximum of {max_files_limit} image files can be converted in a single job.",
            )

        self.validate_config(context.config)

        # 1. Order input files
        file_order = context.config.get("file_order") or context.config.get("image_order")
        if file_order:
            input_files_map = {f["id"]: f for f in context.input_files}
            name_map = {f.get("original_name"): f for f in context.input_files}
            ordered_files: list[dict[str, Any]] = []

            for item in file_order:
                if item in input_files_map:
                    ordered_files.append(input_files_map[item])
                elif item in name_map:
                    ordered_files.append(name_map[item])

            for f in context.input_files:
                if f not in ordered_files:
                    ordered_files.append(f)
        else:
            ordered_files = list(context.input_files)

        # 2. Extract options
        orientation_opt = context.config.get("orientation", "auto").lower()
        page_size_opt = context.config.get("page_size", "fit").lower()
        margin_opt = context.config.get("margin", "none")
        margin_pt = self._resolve_margin(margin_opt)

        custom_filename = context.config.get("output_filename")
        if custom_filename and isinstance(custom_filename, str):
            clean_name = os.path.basename(custom_filename).strip()
            if not clean_name.lower().endswith(".pdf"):
                clean_name = f"{clean_name}.pdf"
            output_filename = clean_name
        else:
            output_filename = "converted_images.pdf"

        # 3. Setup output file path
        output_path = os.path.join(context.temp_dir, f"output_{context.job_id}.pdf")
        pdf_canvas = canvas.Canvas(output_path)

        # Configurable limits
        max_file_size_mb = getattr(settings, "JPG_TO_PDF_MAX_FILE_SIZE_MB", 25)
        max_file_size_bytes = max_file_size_mb * 1024 * 1024
        max_dim = getattr(settings, "JPG_TO_PDF_MAX_IMAGE_DIMENSION", 10000)
        max_total_pixels = getattr(settings, "JPG_TO_PDF_MAX_TOTAL_PIXELS", 150_000_000)
        max_output_mb = getattr(settings, "JPG_TO_PDF_MAX_OUTPUT_PDF_MB", 100)
        max_output_bytes = max_output_mb * 1024 * 1024

        cumulative_pixels = 0
        total_images = len(ordered_files)

        try:
            for idx, file_meta in enumerate(ordered_files):
                local_path = file_meta.get("local_path")
                original_name = file_meta.get("original_name", f"image_{idx + 1}.jpg")

                if not local_path or not os.path.exists(local_path):
                    raise AppException(
                        status_code=404,
                        code="FILE_NOT_FOUND",
                        message=f"Local image file not found: {original_name}",
                    )

                file_size = os.path.getsize(local_path)
                if file_size == 0:
                    raise AppException(
                        status_code=400,
                        code="EMPTY_FILE",
                        message=f"The uploaded image file '{original_name}' is empty (0 bytes).",
                    )

                if file_size > max_file_size_bytes:
                    raise AppException(
                        status_code=413,
                        code="FILE_TOO_LARGE",
                        message=f"Image file '{original_name}' exceeds maximum allowed size of {max_file_size_mb} MB.",
                    )

                # Validate JPEG header signature (0xFF, 0xD8, 0xFF)
                with open(local_path, "rb") as f_chk:
                    header = f_chk.read(3)
                    if header != b"\xff\xd8\xff":
                        raise AppException(
                            status_code=415,
                            code="INVALID_CONTENT_TYPE",
                            message=f"File '{original_name}' is not a valid JPEG image (missing JPEG signature).",
                        )

                # Validate image integrity with PIL
                try:
                    with Image.open(local_path) as test_img:
                        test_img.verify()
                except Exception:
                    raise AppException(
                        status_code=400,
                        code="CORRUPTED_IMAGE",
                        message=f"Image file '{original_name}' is corrupted or cannot be decoded.",
                    )

                # Re-open for actual processing and dimension verification
                with Image.open(local_path) as raw_img:
                    # Apply EXIF rotation if present
                    try:
                        proc_img = ImageOps.exif_transpose(raw_img)
                    except Exception:
                        proc_img = raw_img

                    img_w, img_h = proc_img.size

                    if img_w <= 0 or img_h <= 0:
                        raise AppException(
                            status_code=400,
                            code="INVALID_IMAGE",
                            message=f"Image '{original_name}' has invalid dimensions ({img_w}x{img_h}).",
                        )

                    if img_w > max_dim or img_h > max_dim:
                        raise AppException(
                            status_code=413,
                            code="RESOURCE_LIMIT_EXCEEDED",
                            message=(
                                f"Image '{original_name}' dimension ({img_w}x{img_h} px) "
                                f"exceeds maximum allowed dimension of {max_dim} px."
                            ),
                        )

                    cumulative_pixels += (img_w * img_h)
                    if cumulative_pixels > max_total_pixels:
                        raise AppException(
                            status_code=413,
                            code="RESOURCE_LIMIT_EXCEEDED",
                            message=(
                                f"Total pixels across images ({cumulative_pixels:,} px) "
                                f"exceeds maximum allowed limit of {max_total_pixels:,} px."
                            ),
                        )

                    # Compute page and drawing rectangle
                    page_w, page_h, draw_x, draw_y, draw_w, draw_h = self._calculate_page_and_draw_rect(
                        img_w=img_w,
                        img_h=img_h,
                        page_size_opt=page_size_opt,
                        orientation_opt=orientation_opt,
                        margin_pt=margin_pt,
                    )

                    pdf_canvas.setPageSize((page_w, page_h))
                    reader = ImageReader(proc_img)
                    pdf_canvas.drawImage(
                        reader,
                        draw_x,
                        draw_y,
                        width=draw_w,
                        height=draw_h,
                    )
                    pdf_canvas.showPage()

                # Report incremental progress (10% to 90%)
                progress_val = 10 + int(((idx + 1) / total_images) * 80)
                await context.progress_callback(min(progress_val, 90))

            # 4. Finalize PDF
            pdf_canvas.save()

            if not os.path.exists(output_path):
                raise AppException(
                    status_code=500,
                    code="PROCESSING_ERROR",
                    message="Failed to generate output PDF file.",
                )

            output_size = os.path.getsize(output_path)
            if output_size > max_output_bytes:
                if os.path.exists(output_path):
                    os.unlink(output_path)
                raise AppException(
                    status_code=413,
                    code="OUTPUT_TOO_LARGE",
                    message=(
                        f"Generated PDF size ({output_size / (1024 * 1024):.1f} MB) "
                        f"exceeds maximum allowed limit of {max_output_mb} MB."
                    ),
                )

            # 5. Compute SHA-256
            hasher = hashlib.sha256()
            with open(output_path, "rb") as f_out:
                for chunk in iter(lambda: f_out.read(65536), b""):
                    hasher.update(chunk)
            sha256_hash = hasher.hexdigest()

            await context.progress_callback(95)

            return {
                "output_path": output_path,
                "filename": output_filename,
                "size_bytes": output_size,
                "page_count": total_images,
                "file_count": total_images,
                "sha256": sha256_hash,
                "content_type": "application/pdf",
            }

        except Exception:
            # Guarantee cleanup of generated output PDF on any failure
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except OSError:
                    pass
            raise
