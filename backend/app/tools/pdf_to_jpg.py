import hashlib
import io
import os
import zipfile
from typing import Dict, Any, List
from PIL import Image
import pypdfium2 as pdfium
from pypdfium2._helpers.misc import PdfiumError
import pypdf
from pypdf.errors import PdfReadError, PyPdfError

from app.core.config import settings
from app.core.errors import AppException
from app.tools.base import ToolHandler, ProcessingContext


class PdfToJpgPDFHandler(ToolHandler):
    """
    Renders every page of an input PDF into high-quality JPEG images and packages them
    into a structured ZIP archive.
    """

    tool_id = "pdf_to_jpg"
    display_name = "PDF to JPG"
    min_input_files = 1
    max_input_files = 1
    accepted_content_types = ["application/pdf"]

    def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validates configuration options for PDF to JPG conversion.
        Supported options:
          - dpi: int, 72 to 600 (default: 150)
          - quality: int, 1 to 100 (default: 85)
          - output_filename: Optional[str]
        """
        if not isinstance(config, dict):
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Config must be a valid dictionary.",
            )

        dpi = config.get("dpi", 150)
        if not isinstance(dpi, int) or dpi < 72 or dpi > 600:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Resolution (DPI) must be an integer between 72 and 600 (e.g. 150 for standard, 300 for high).",
            )

        quality = config.get("quality", 85)
        if not isinstance(quality, int) or quality < 1 or quality > 100:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message="Image quality must be an integer between 1 and 100.",
            )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """
        Converts the input PDF pages into individual JPG images and saves them in a ZIP archive.
        Enforces configurable upload size, page count, and render dimension limits,
        releasing all native and file resources reliably.
        """
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_INPUT_COUNT",
                message=f"PDF to JPG requires exactly 1 input file, received {len(context.input_files)}.",
            )

        self.validate_config(context.config)

        input_file_meta = context.input_files[0]
        local_path = input_file_meta["local_path"]
        original_name = input_file_meta.get("original_name", "document.pdf")

        # 1. Basic file existence and size checks
        if not os.path.exists(local_path):
            raise AppException(
                status_code=404,
                code="FILE_NOT_FOUND",
                message=f"Local input file not found: {original_name}",
            )

        file_size = os.path.getsize(local_path)
        if file_size == 0:
            raise AppException(
                status_code=400,
                code="EMPTY_FILE",
                message=f"The uploaded PDF file '{original_name}' is empty (0 bytes).",
            )

        max_size_mb = getattr(settings, "PDF_TO_JPG_MAX_FILE_SIZE_MB", 50)
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise AppException(
                status_code=413,
                code="FILE_TOO_LARGE",
                message=f"File '{original_name}' exceeds maximum allowed size of {max_size_mb} MB for PDF to JPG conversion.",
            )

        # 2. Check header magic bytes
        with open(local_path, "rb") as f_chk:
            header = f_chk.read(5)
            if header != b"%PDF-":
                raise AppException(
                    status_code=400,
                    code="INVALID_PDF",
                    message=f"File '{original_name}' is not a valid PDF document.",
                )

        # 3. Check for encryption using pypdf as pre-check
        try:
            with open(local_path, "rb") as f_chk:
                reader = pypdf.PdfReader(f_chk)
                if reader.is_encrypted:
                    raise AppException(
                        status_code=400,
                        code="PDF_ENCRYPTED",
                        message=f"File '{original_name}' is password-protected and cannot be converted to JPG.",
                    )
        except AppException:
            raise
        except (PdfReadError, PyPdfError):
            pass

        # 4. Open document with pypdfium2
        try:
            doc = pdfium.PdfDocument(local_path)
        except PdfiumError as e:
            err_msg = str(e).lower()
            if "password" in err_msg:
                raise AppException(
                    status_code=400,
                    code="PDF_ENCRYPTED",
                    message=f"File '{original_name}' is password-protected and cannot be converted to JPG.",
                )
            raise AppException(
                status_code=400,
                code="INVALID_PDF",
                message=f"Failed to parse PDF document '{original_name}'. The file may be corrupted.",
            )
        except Exception:
            raise AppException(
                status_code=400,
                code="INVALID_PDF",
                message=f"Failed to parse PDF document '{original_name}'. The file may be corrupted.",
            )

        try:
            total_pages = len(doc)
            if total_pages == 0:
                raise AppException(
                    status_code=400,
                    code="EMPTY_PDF",
                    message=f"The PDF file '{original_name}' contains no readable pages.",
                )

            dpi = context.config.get("dpi", 150)
            quality = context.config.get("quality", 85)
            scale = dpi / 72.0

            # 5. Check sensible page-count limits
            max_pages_300 = getattr(settings, "PDF_TO_JPG_MAX_PAGES_300_DPI", 50)
            max_pages_default = getattr(settings, "PDF_TO_JPG_MAX_PAGES_DEFAULT", 100)
            max_pages = max_pages_300 if dpi > 150 else max_pages_default
            if total_pages > max_pages:
                raise AppException(
                    status_code=400,
                    code="EXCESSIVE_PAGE_COUNT",
                    message=f"PDF '{original_name}' has {total_pages} pages, which exceeds the limit of {max_pages} pages for {dpi} DPI conversion.",
                )

            base_name = original_name.rsplit(".", 1)[0]
            output_filename = context.config.get("output_filename") or f"{base_name}_images.zip"
            if not output_filename.lower().endswith(".zip"):
                output_filename += ".zip"

            output_path = os.path.join(context.temp_dir, "output.zip")
            pad_width = max(len(str(total_pages)), 2)

            max_dim = getattr(settings, "PDF_TO_JPG_MAX_RENDER_DIMENSION", 8000)
            max_pixels = getattr(settings, "PDF_TO_JPG_MAX_RENDER_PIXELS", 36_000_000)
            max_aggregate_mb = getattr(settings, "PDF_TO_JPG_MAX_AGGREGATE_OUTPUT_MB", 250)
            max_aggregate_bytes = max_aggregate_mb * 1024 * 1024
            total_generated_bytes = 0

            # 6. Render pages and write incrementally to ZIP archive
            try:
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
                    for idx in range(total_pages):
                        page = None
                        bitmap = None
                        try:
                            page = doc.get_page(idx)
                            width_pt, height_pt = page.get_size()
                            render_w = int(width_pt * scale)
                            render_h = int(height_pt * scale)

                            if render_w > max_dim or render_h > max_dim or (render_w * render_h) > max_pixels:
                                raise AppException(
                                    status_code=400,
                                    code="PAGE_DIMENSIONS_TOO_LARGE",
                                    message=(
                                        f"Page {idx + 1} dimensions ({render_w}x{render_h} px at {dpi} DPI) "
                                        f"exceed the maximum allowed rendering limits ({max_dim} px / {max_pixels:,} total pixels)."
                                    ),
                                )

                            bitmap = page.render(scale=scale)
                            pil_img: Image.Image = bitmap.to_pil()
                            if pil_img.mode != "RGB":
                                pil_img = pil_img.convert("RGB")

                            buf = io.BytesIO()
                            pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
                            img_bytes = buf.getvalue()

                            total_generated_bytes += len(img_bytes)
                            if total_generated_bytes > max_aggregate_bytes:
                                raise AppException(
                                    status_code=413,
                                    code="OUTPUT_SIZE_LIMIT_EXCEEDED",
                                    message=(
                                        f"Aggregate generated output size exceeded maximum allowed limit of "
                                        f"{max_aggregate_mb} MB for PDF to JPG conversion."
                                    ),
                                )

                            entry_name = f"page_{idx + 1:0{pad_width}d}.jpg"
                            zip_out.writestr(entry_name, img_bytes)

                            if os.path.exists(output_path) and os.path.getsize(output_path) > max_aggregate_bytes:
                                raise AppException(
                                    status_code=413,
                                    code="OUTPUT_SIZE_LIMIT_EXCEEDED",
                                    message=(
                                        f"Generated ZIP archive size exceeded maximum allowed limit of "
                                        f"{max_aggregate_mb} MB for PDF to JPG conversion."
                                    ),
                                )
                        except AppException:
                            raise
                        except Exception as e:
                            raise AppException(
                                status_code=500,
                                code="RENDER_ERROR",
                                message=f"Error rendering page {idx + 1} of '{original_name}': {str(e)}",
                            )
                        finally:
                            if bitmap is not None:
                                bitmap.close()
                            if page is not None:
                                page.close()

                        # Report progress
                        progress = 10 + int(80 * (idx + 1) / total_pages)
                        if context.progress_callback:
                            cb = context.progress_callback(progress)
                            if hasattr(cb, "__await__"):
                                await cb
            except Exception:
                # Remove partially generated output ZIP if an error occurred during rendering
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                raise
        finally:
            doc.close()

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
            "page_count": total_pages,
            "file_count": total_pages,
            "dpi": dpi,
            "quality": quality,
            "sha256": sha256_hash,
        }
