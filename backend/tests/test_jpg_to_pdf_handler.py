import io
import os
import pytest
from PIL import Image
import pypdf

from app.core.config import settings
from app.core.errors import AppException
from app.tools.jpg_to_pdf import JpgToPdfPDFHandler
from app.tools.base import ProcessingContext


def create_test_jpeg(width: int = 300, height: int = 200, color: tuple = (255, 100, 50)) -> bytes:
    """Helper to generate a valid in-memory JPEG byte string."""
    bio = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(bio, format="JPEG", quality=85)
    return bio.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    progress_calls = []

    async def dummy_progress(p: int):
        progress_calls.append(p)

    ctx = ProcessingContext(
        job_id="test-job-jpg-to-pdf",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )
    ctx._progress_calls = progress_calls
    return ctx


@pytest.mark.asyncio
async def test_jpg_to_pdf_single_image_default(tmp_path):
    handler = JpgToPdfPDFHandler()
    img_bytes = create_test_jpeg(400, 300)
    img_file = tmp_path / "img1.jpg"
    img_file.write_bytes(img_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"id": "file-1", "original_name": "img1.jpg", "local_path": str(img_file)}],
        config={},
    )
    result = await handler.process(ctx)

    assert os.path.exists(result["output_path"])
    assert result["filename"] == "converted_images.pdf"
    assert result["page_count"] == 1
    assert result["file_count"] == 1
    assert result["size_bytes"] > 0
    assert result["sha256"] is not None

    # Verify generated PDF with pypdf
    with open(result["output_path"], "rb") as f_out:
        reader = pypdf.PdfReader(f_out)
        assert len(reader.pages) == 1
        page = reader.pages[0]
        # In fit mode with margin none, dimensions should match 400x300 pt
        assert round(float(page.mediabox.width)) == 400
        assert round(float(page.mediabox.height)) == 300


@pytest.mark.asyncio
async def test_jpg_to_pdf_multiple_images_ordering(tmp_path):
    handler = JpgToPdfPDFHandler()
    # Create 3 images with different distinct sizes and colors
    img1_bytes = create_test_jpeg(100, 200, (255, 0, 0))
    img2_bytes = create_test_jpeg(300, 400, (0, 255, 0))
    img3_bytes = create_test_jpeg(500, 600, (0, 0, 255))

    p1 = tmp_path / "first.jpg"
    p2 = tmp_path / "second.jpg"
    p3 = tmp_path / "third.jpg"
    p1.write_bytes(img1_bytes)
    p2.write_bytes(img2_bytes)
    p3.write_bytes(img3_bytes)

    # Supply in order p1, p2, p3, but request reordering via file_order: [id-3, id-1, id-2]
    input_files = [
        {"id": "id-1", "original_name": "first.jpg", "local_path": str(p1)},
        {"id": "id-2", "original_name": "second.jpg", "local_path": str(p2)},
        {"id": "id-3", "original_name": "third.jpg", "local_path": str(p3)},
    ]

    ctx = make_context(
        str(tmp_path),
        input_files,
        config={"file_order": ["id-3", "id-1", "id-2"], "page_size": "fit", "margin": "none"},
    )
    result = await handler.process(ctx)

    assert result["page_count"] == 3
    with open(result["output_path"], "rb") as f_out:
        reader = pypdf.PdfReader(f_out)
        assert len(reader.pages) == 3
        # Page 1 should correspond to id-3 (500x600)
        assert round(float(reader.pages[0].mediabox.width)) == 500
        assert round(float(reader.pages[0].mediabox.height)) == 600
        # Page 2 should correspond to id-1 (100x200)
        assert round(float(reader.pages[1].mediabox.width)) == 100
        assert round(float(reader.pages[1].mediabox.height)) == 200
        # Page 3 should correspond to id-2 (300x400)
        assert round(float(reader.pages[2].mediabox.width)) == 300
        assert round(float(reader.pages[2].mediabox.height)) == 400


@pytest.mark.asyncio
async def test_jpg_to_pdf_page_sizes_and_orientations(tmp_path):
    handler = JpgToPdfPDFHandler()
    img_bytes = create_test_jpeg(800, 600)  # landscape aspect ratio
    p = tmp_path / "test.jpg"
    p.write_bytes(img_bytes)

    # 1. A4 Portrait
    ctx_a4_p = make_context(
        str(tmp_path),
        [{"id": "f1", "original_name": "test.jpg", "local_path": str(p)}],
        config={"page_size": "a4", "orientation": "portrait", "margin": "small"},
    )
    res_a4_p = await handler.process(ctx_a4_p)
    with open(res_a4_p["output_path"], "rb") as f_out:
        reader = pypdf.PdfReader(f_out)
        page = reader.pages[0]
        # A4 portrait: width < height (~595 x ~842)
        assert float(page.mediabox.width) < float(page.mediabox.height)
        assert abs(float(page.mediabox.width) - 595.28) < 1.0

    # 2. Letter Landscape
    ctx_let_l = make_context(
        str(tmp_path),
        [{"id": "f1", "original_name": "test.jpg", "local_path": str(p)}],
        config={"page_size": "letter", "orientation": "landscape", "margin": "normal"},
    )
    res_let_l = await handler.process(ctx_let_l)
    with open(res_let_l["output_path"], "rb") as f_out:
        reader = pypdf.PdfReader(f_out)
        page = reader.pages[0]
        # Letter landscape: width > height (~792 x ~612)
        assert float(page.mediabox.width) > float(page.mediabox.height)
        assert abs(float(page.mediabox.width) - 792.0) < 1.0

    # 3. Fit mode with normal margin
    ctx_fit_m = make_context(
        str(tmp_path),
        [{"id": "f1", "original_name": "test.jpg", "local_path": str(p)}],
        config={"page_size": "fit", "orientation": "auto", "margin": "normal"},
    )
    res_fit_m = await handler.process(ctx_fit_m)
    with open(res_fit_m["output_path"], "rb") as f_out:
        reader = pypdf.PdfReader(f_out)
        page = reader.pages[0]
        # Normal margin is 36 pt. Page width should be 800 + 2*36 = 872
        assert round(float(page.mediabox.width)) == 872
        assert round(float(page.mediabox.height)) == 672


@pytest.mark.asyncio
async def test_jpg_to_pdf_invalid_format_non_jpeg(tmp_path):
    handler = JpgToPdfPDFHandler()
    fake_jpg = tmp_path / "fake.jpg"
    fake_jpg.write_text("This is not a real JPEG file", encoding="utf-8")

    ctx = make_context(
        str(tmp_path),
        [{"id": "fake", "original_name": "fake.jpg", "local_path": str(fake_jpg)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "INVALID_CONTENT_TYPE"
    assert "missing JPEG signature" in exc_info.value.message


@pytest.mark.asyncio
async def test_jpg_to_pdf_corrupted_jpeg(tmp_path):
    handler = JpgToPdfPDFHandler()
    corrupt_jpg = tmp_path / "corrupt.jpg"
    # Magic bytes for JPEG followed by random junk that cannot be decoded
    corrupt_jpg.write_bytes(b"\xff\xd8\xff\x00\x01\x02\x03\x04\x05junkdatahere")

    ctx = make_context(
        str(tmp_path),
        [{"id": "corrupt", "original_name": "corrupt.jpg", "local_path": str(corrupt_jpg)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code in ("CORRUPTED_IMAGE", "INVALID_IMAGE")


@pytest.mark.asyncio
async def test_jpg_to_pdf_empty_file(tmp_path):
    handler = JpgToPdfPDFHandler()
    empty_file = tmp_path / "empty.jpg"
    empty_file.write_bytes(b"")

    ctx = make_context(
        str(tmp_path),
        [{"id": "empty", "original_name": "empty.jpg", "local_path": str(empty_file)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_jpg_to_pdf_oversized_file_limit(tmp_path, monkeypatch):
    handler = JpgToPdfPDFHandler()
    img_bytes = create_test_jpeg(100, 100)
    p = tmp_path / "oversized.jpg"
    p.write_bytes(img_bytes)

    # Mock settings.JPG_TO_PDF_MAX_FILE_SIZE_MB to a tiny threshold
    monkeypatch.setattr(settings, "JPG_TO_PDF_MAX_FILE_SIZE_MB", 0)

    ctx = make_context(
        str(tmp_path),
        [{"id": "ov", "original_name": "oversized.jpg", "local_path": str(p)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_jpg_to_pdf_dimension_limit(tmp_path, monkeypatch):
    handler = JpgToPdfPDFHandler()
    img_bytes = create_test_jpeg(200, 200)
    p = tmp_path / "dim.jpg"
    p.write_bytes(img_bytes)

    # Mock settings.JPG_TO_PDF_MAX_IMAGE_DIMENSION to 150 px
    monkeypatch.setattr(settings, "JPG_TO_PDF_MAX_IMAGE_DIMENSION", 150)

    ctx = make_context(
        str(tmp_path),
        [{"id": "dim", "original_name": "dim.jpg", "local_path": str(p)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "RESOURCE_LIMIT_EXCEEDED"
    assert "exceeds maximum allowed dimension" in exc_info.value.message


@pytest.mark.asyncio
async def test_jpg_to_pdf_total_pixels_limit(tmp_path, monkeypatch):
    handler = JpgToPdfPDFHandler()
    img_bytes = create_test_jpeg(100, 100)  # 10,000 px
    p = tmp_path / "pixels.jpg"
    p.write_bytes(img_bytes)

    # Mock settings.JPG_TO_PDF_MAX_TOTAL_PIXELS to 5,000 px
    monkeypatch.setattr(settings, "JPG_TO_PDF_MAX_TOTAL_PIXELS", 5000)

    ctx = make_context(
        str(tmp_path),
        [{"id": "px", "original_name": "pixels.jpg", "local_path": str(p)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "RESOURCE_LIMIT_EXCEEDED"
    assert "Total pixels across images" in exc_info.value.message


@pytest.mark.asyncio
async def test_jpg_to_pdf_too_many_files(tmp_path, monkeypatch):
    handler = JpgToPdfPDFHandler()
    monkeypatch.setattr(settings, "JPG_TO_PDF_MAX_FILES", 2)

    files = [
        {"id": f"f{i}", "original_name": f"f{i}.jpg", "local_path": "/fake/path"}
        for i in range(3)
    ]
    ctx = make_context(str(tmp_path), files)

    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "TOO_MANY_FILES"


@pytest.mark.asyncio
async def test_jpg_to_pdf_cleanup_on_failure(tmp_path, monkeypatch):
    handler = JpgToPdfPDFHandler()
    # Mock settings to trigger output too large
    monkeypatch.setattr(settings, "JPG_TO_PDF_MAX_OUTPUT_PDF_MB", 0)

    img_bytes = create_test_jpeg(100, 100)
    p = tmp_path / "test.jpg"
    p.write_bytes(img_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"id": "f1", "original_name": "test.jpg", "local_path": str(p)}],
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)

    assert exc_info.value.code == "OUTPUT_TOO_LARGE"
    # Ensure temporary output PDF was removed
    out_pdf = tmp_path / f"output_{ctx.job_id}.pdf"
    assert not out_pdf.exists()
