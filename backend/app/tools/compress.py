import hashlib
import io
import os
import shutil
from typing import Dict, Any, Set
import pikepdf
from PIL import Image

from app.core.errors import AppException
from app.core.logging import logger
from app.tools.base import ToolHandler, ProcessingContext


class CompressPDFHandler(ToolHandler):
    """
    Handler for compressing PDF files.
    Optimizes PDF internal structure, removes orphaned objects, enables object streams,
    compresses content streams, and downsamples / re-compresses embedded raster images.
    """

    LEVEL_SETTINGS = {
        "recommended": {
            "jpeg_quality": 80,
            "max_dim": 1600,
        },
        "balanced": {
            "jpeg_quality": 60,
            "max_dim": 1200,
        },
        "maximum": {
            "jpeg_quality": 40,
            "max_dim": 800,
        },
    }

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validates compression level and configuration parameters."""
        if not config:
            return

        level = config.get("level", "recommended").lower()
        if level not in self.LEVEL_SETTINGS:
            raise AppException(
                status_code=400,
                code="INVALID_CONFIG",
                message=f"Invalid compression level '{level}'. Supported levels are: recommended, balanced, maximum.",
            )

    async def process(self, context: ProcessingContext) -> Dict[str, Any]:
        """
        Executes PDF compression pipeline.
        Re-encodes images if beneficial, applies stream compression and object streams,
        and ensures that if the result is larger than the original, the original is retained.
        """
        # 1. Validate input file count
        if len(context.input_files) != 1:
            raise AppException(
                status_code=400,
                code="INVALID_FILE_COUNT",
                message="Compress PDF requires exactly 1 input file.",
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

        # 2. Parse configuration
        level = context.config.get("level", "recommended").lower()
        if level not in self.LEVEL_SETTINGS:
            level = "recommended"
        settings = self.LEVEL_SETTINGS[level]
        jpeg_quality = settings["jpeg_quality"]
        max_dim = settings["max_dim"]

        # 3. Read PDF with pikepdf
        pdf = None
        try:
            pdf = pikepdf.Pdf.open(local_path)
        except pikepdf.PasswordError:
            raise AppException(
                status_code=400,
                code="PDF_ENCRYPTED",
                message=f"File '{original_name}' is password-protected and cannot be compressed.",
            )
        except Exception as e:
            raise AppException(
                status_code=400,
                code="CORRUPTED_PDF",
                message=f"File '{original_name}' is corrupted or not a valid PDF: {str(e)}",
            )

        try:
            total_pages = len(pdf.pages)
            if total_pages == 0:
                raise AppException(
                    status_code=400,
                    code="EMPTY_PDF",
                    message=f"File '{original_name}' contains no readable pages.",
                )

            # 4. Image optimization pass across pages
            visited_streams: Set[int] = set()

            for page_idx, page in enumerate(pdf.pages):
                try:
                    images_dict = page.get_images()
                except Exception as e:
                    logger.warning(f"Could not inspect images on page {page_idx + 1}: {e}")
                    images_dict = {}

                for img_name, raw_stream in images_dict.items():
                    stream_obj_id = id(raw_stream)
                    if stream_obj_id in visited_streams:
                        continue
                    visited_streams.add(stream_obj_id)

                    try:
                        # Skip if stream has transparency mask or soft mask to preserve fidelity
                        if "/SMask" in raw_stream or "/Mask" in raw_stream:
                            continue

                        pdf_image = pikepdf.PdfImage(raw_stream)
                        pil_img = pdf_image.as_pil_image()

                        # Skip 1-bit monochrome masks, palettes with transparency, or unusual modes
                        if pil_img.mode in ("1", "P", "RGBA", "LA"):
                            continue

                        original_stream_bytes = len(raw_stream.read_raw_bytes())

                        # Downscale large dimensions
                        w, h = pil_img.size
                        needs_resize = (w > max_dim or h > max_dim)
                        if needs_resize:
                            pil_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                        # Convert CMYK to RGB for consistent JPEG encoding
                        if pil_img.mode == "CMYK":
                            pil_img = pil_img.convert("RGB")

                        buf = io.BytesIO()
                        pil_img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
                        compressed_img_bytes = buf.getvalue()

                        # Only replace if newly compressed image is actually smaller
                        if len(compressed_img_bytes) < original_stream_bytes:
                            raw_stream.write(compressed_img_bytes, filter=pikepdf.Name.DCTDecode)
                            raw_stream.Width = pil_img.width
                            raw_stream.Height = pil_img.height
                            raw_stream.ColorSpace = (
                                pikepdf.Name.DeviceRGB if pil_img.mode == "RGB" else pikepdf.Name.DeviceGray
                            )
                            raw_stream.BitsPerComponent = 8
                            # Remove old unneeded filter parameters
                            if "/DecodeParms" in raw_stream:
                                del raw_stream["/DecodeParms"]

                    except Exception as img_err:
                        # Non-critical: preserve original image if processing fails
                        logger.debug(f"Skipping image {img_name} optimization: {img_err}")
                        continue

                # Report progress during image pass (from 15% to 75%)
                progress = 15 + int(60 * (page_idx + 1) / total_pages)
                if context.progress_callback:
                    res = context.progress_callback(progress)
                    if hasattr(res, "__await__"):
                        await res

            # 5. Save optimized PDF with stream compression and object streams
            temp_output = os.path.join(context.temp_dir, "compressed_temp.pdf")
            pdf.save(
                temp_output,
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

            # Close pikepdf document before file operations
            pdf.close()
            pdf = None

            temp_size = os.path.getsize(temp_output)

            output_filename = context.config.get("output_filename") or f"compressed_{original_name}"
            if not output_filename.lower().endswith(".pdf"):
                output_filename += ".pdf"

            final_output_path = os.path.join(context.temp_dir, "output.pdf")

            # 6. Verify if output size is actually smaller
            # If the compressed output is larger or equal (e.g. document was already optimal),
            # retain the original file and report 0 savings rather than a negative number.
            if temp_size >= input_size:
                logger.info(
                    f"PDF '{original_name}' was already optimal or could not be reduced "
                    f"({input_size} -> {temp_size} bytes). Retaining original file."
                )
                if os.path.abspath(local_path) != os.path.abspath(final_output_path):
                    shutil.copy2(local_path, final_output_path)
                if os.path.exists(temp_output):
                    try:
                        os.remove(temp_output)
                    except Exception:
                        pass
                final_size = input_size
                savings_bytes = 0
                savings_percentage = 0.0
                is_already_optimal = True
            else:
                shutil.move(temp_output, final_output_path)
                final_size = temp_size
                savings_bytes = input_size - final_size
                savings_percentage = round((savings_bytes / input_size) * 100, 2)
                is_already_optimal = False

            # 7. Compute SHA-256 hash
            sha256 = hashlib.sha256()
            with open(final_output_path, "rb") as f_out:
                while chunk := f_out.read(65536):
                    sha256.update(chunk)
            sha256_hash = sha256.hexdigest()

            return {
                "output_path": final_output_path,
                "filename": output_filename,
                "size_bytes": final_size,
                "page_count": total_pages,
                "original_size_bytes": input_size,
                "savings_bytes": savings_bytes,
                "savings_percentage": savings_percentage,
                "is_already_optimal": is_already_optimal,
                "compression_level": level,
                "content_type": "application/pdf",
                "sha256": sha256_hash,
            }

        finally:
            if pdf is not None:
                try:
                    pdf.close()
                except Exception:
                    pass
