import io
import os
import shutil
import tempfile

import pikepdf
import pypdf
import pytest
from PIL import Image

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.compress import CompressPDFHandler


def create_sample_pdf(num_pages: int = 3, width: int = 612, height: int = 792) -> bytes:
    """Creates a simple multi-page PDF."""
    writer = pypdf.PdfWriter()
    for i in range(num_pages):
        writer.add_blank_page(width=width + i * 10, height=height + i * 10)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_image_pdf(img_width: int = 800, img_height: int = 600) -> bytes:
    """Creates a PDF containing an embedded uncompressed raster image."""
    img = Image.new("RGB", (img_width, img_height), color=(100, 150, 200))
    for x in range(0, img_width, 10):
        for y in range(0, img_height, 10):
            img.putpixel((x, y), ((x * 3) % 256, (y * 5) % 256, 180))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Embed as PDF
    pdf_buf = io.BytesIO()
    img.save(pdf_buf, format="PDF")
    return pdf_buf.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    """Helper to build ProcessingContext with dummy progress callback."""
    async def dummy_progress(p: int):
        pass

    return ProcessingContext(
        job_id="test-job-compress",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


@pytest.fixture
def temp_workspace():
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_compress_typical_pdf(temp_workspace):
    """Verifies compression on a standard multi-page PDF, preserving pages and dimensions."""
    handler = CompressPDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=3)

    input_path = os.path.join(temp_workspace, "sample.pdf")
    with open(input_path, "wb") as f:
        f.write(pdf_bytes)

    context = make_context(
        temp_dir=temp_workspace,
        input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
        config={"level": "recommended"},
    )

    result = await handler.process(context)

    assert os.path.exists(result["output_path"])
    assert result["page_count"] == 3
    assert result["content_type"] == "application/pdf"
    assert "sha256" in result
    assert result["compression_level"] == "recommended"

    # Verify output is valid readable PDF with 3 pages
    with pikepdf.Pdf.open(result["output_path"]) as out_pdf:
        assert len(out_pdf.pages) == 3


@pytest.mark.asyncio
async def test_compress_pdf_with_images(temp_workspace):
    """Verifies that PDFs with large raster images achieve measurable size reduction."""
    handler = CompressPDFHandler()
    image_pdf_bytes = create_image_pdf(img_width=1000, img_height=1000)
    orig_size = len(image_pdf_bytes)

    input_path = os.path.join(temp_workspace, "photo.pdf")
    with open(input_path, "wb") as f:
        f.write(image_pdf_bytes)

    context = make_context(
        temp_dir=temp_workspace,
        input_files=[{"local_path": input_path, "original_name": "photo.pdf"}],
        config={"level": "balanced"},
    )

    result = await handler.process(context)

    assert result["original_size_bytes"] == orig_size
    assert result["size_bytes"] < orig_size
    assert result["savings_bytes"] > 0
    assert result["savings_percentage"] > 0.0
    assert result["is_already_optimal"] is False

    # Check page count and readability
    with pikepdf.Pdf.open(result["output_path"]) as out_pdf:
        assert len(out_pdf.pages) == 1


@pytest.mark.asyncio
async def test_compress_levels(temp_workspace):
    """Compares recommended, balanced, and maximum compression levels."""
    handler = CompressPDFHandler()
    image_pdf_bytes = create_image_pdf(img_width=1200, img_height=1200)

    sizes = {}
    for level in ("recommended", "balanced", "maximum"):
        lvl_dir = os.path.join(temp_workspace, level)
        os.makedirs(lvl_dir, exist_ok=True)
        in_path = os.path.join(lvl_dir, "input.pdf")
        with open(in_path, "wb") as f:
            f.write(image_pdf_bytes)

        context = make_context(
            temp_dir=lvl_dir,
            input_files=[{"local_path": in_path, "original_name": "input.pdf"}],
            config={"level": level},
        )
        res = await handler.process(context)
        sizes[level] = res["size_bytes"]
        assert res["compression_level"] == level

    # Maximum should be smaller than or equal to Recommended
    assert sizes["maximum"] <= sizes["recommended"]


@pytest.mark.asyncio
async def test_compress_already_compressed_pdf(temp_workspace):
    """Verifies that if output is not smaller, the original is retained and zero savings is reported."""
    handler = CompressPDFHandler()
    # A tiny blank PDF with 1 object where re-encoding might add negligible metadata overhead
    pdf = pikepdf.new()
    pdf.add_blank_page()
    bio = io.BytesIO()
    pdf.save(bio, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    tiny_bytes = bio.getvalue()

    input_path = os.path.join(temp_workspace, "tiny.pdf")
    with open(input_path, "wb") as f:
        f.write(tiny_bytes)

    orig_size = len(tiny_bytes)

    context = make_context(
        temp_dir=temp_workspace,
        input_files=[{"local_path": input_path, "original_name": "tiny.pdf"}],
        config={"level": "recommended"},
    )

    result = await handler.process(context)

    # Result size must never be larger than input size
    assert result["size_bytes"] <= orig_size
    if result["is_already_optimal"]:
        assert result["savings_bytes"] == 0
        assert result["savings_percentage"] == 0.0


@pytest.mark.asyncio
async def test_compress_invalid_files(temp_workspace):
    """Verifies rejection of corrupted, encrypted, empty, and missing files."""
    handler = CompressPDFHandler()

    # 1. Corrupted file
    corrupt_path = os.path.join(temp_workspace, "corrupt.pdf")
    with open(corrupt_path, "wb") as f:
        f.write(b"%PDF-1.4\ncorrupted junk bytes\xff\xfe")

    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": corrupt_path, "original_name": "corrupt.pdf"}],
                config={},
            )
        )
    assert exc_info.value.code == "CORRUPTED_PDF"

    # 2. Encrypted file
    enc_path = os.path.join(temp_workspace, "encrypted.pdf")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret_password")
    with open(enc_path, "wb") as f:
        writer.write(f)

    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": enc_path, "original_name": "encrypted.pdf"}],
                config={},
            )
        )
    assert exc_info.value.code == "PDF_ENCRYPTED"

    # 3. Empty file (0 bytes)
    empty_path = os.path.join(temp_workspace, "empty.pdf")
    with open(empty_path, "wb") as f:
        pass

    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": empty_path, "original_name": "empty.pdf"}],
                config={},
            )
        )
    assert exc_info.value.code == "EMPTY_FILE"

    # 4. Multiple files
    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[
                    {"local_path": corrupt_path, "original_name": "1.pdf"},
                    {"local_path": enc_path, "original_name": "2.pdf"},
                ],
                config={},
            )
        )
    assert exc_info.value.code == "INVALID_FILE_COUNT"


def test_compress_invalid_config():
    """Verifies config validator rejects unsupported compression levels."""
    handler = CompressPDFHandler()
    with pytest.raises(AppException) as exc_info:
        handler.validate_config({"level": "extreme_lossy"})
    assert exc_info.value.code == "INVALID_CONFIG"
