import io
import os
import zipfile

import pypdf
import pytest
from PIL import Image

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.pdf_to_jpg import PdfToJpgPDFHandler


def create_sample_pdf(page_count: int = 3) -> bytes:
    """Creates a sample multi-page PDF."""
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        width = 200 + (i * 50)
        height = 300 + (i * 50)
        page = pypdf.PageObject.create_blank_page(width=width, height=height)
        writer.add_page(page)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def create_encrypted_pdf(password: str = "secret") -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt(user_password=password, algorithm="AES-256")
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    async def dummy_progress(p: int):
        pass

    return ProcessingContext(
        job_id="test-job-pdf-to-jpg",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


@pytest.mark.asyncio
async def test_pdf_to_jpg_valid_conversion_default(tmp_path):
    handler = PdfToJpgPDFHandler()
    pdf_bytes = create_sample_pdf(3)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={},
    )
    result = await handler.process(ctx)

    assert result["content_type"] == "application/zip"
    assert result["page_count"] == 3
    assert result["file_count"] == 3
    assert result["dpi"] == 150
    assert result["filename"] == "sample_images.zip"
    assert os.path.exists(result["output_path"])

    # Inspect zip contents
    with zipfile.ZipFile(result["output_path"], "r") as z:
        names = z.namelist()
        assert names == ["page_01.jpg", "page_02.jpg", "page_03.jpg"]
        for name in names:
            data = z.read(name)
            # Verify valid JPEG header
            assert data.startswith(b"\xff\xd8\xff")
            with Image.open(io.BytesIO(data)) as img:
                assert img.format == "JPEG"
                assert img.width > 0
                assert img.height > 0


@pytest.mark.asyncio
async def test_pdf_to_jpg_high_dpi_resolution(tmp_path):
    handler = PdfToJpgPDFHandler()
    pdf_bytes = create_sample_pdf(1)
    in_file = tmp_path / "single.pdf"
    in_file.write_bytes(pdf_bytes)

    # 1. Render at standard 150 DPI
    ctx150 = make_context(
        str(tmp_path),
        [{"original_name": "single.pdf", "local_path": str(in_file)}],
        config={"dpi": 150},
    )
    res150 = await handler.process(ctx150)
    with zipfile.ZipFile(res150["output_path"], "r") as z:
        with Image.open(io.BytesIO(z.read("page_01.jpg"))) as img150:
            w150, h150 = img150.width, img150.height

    # 2. Render at high 300 DPI
    ctx300 = make_context(
        str(tmp_path),
        [{"original_name": "single.pdf", "local_path": str(in_file)}],
        config={"dpi": 300},
    )
    res300 = await handler.process(ctx300)
    with zipfile.ZipFile(res300["output_path"], "r") as z:
        with Image.open(io.BytesIO(z.read("page_01.jpg"))) as img300:
            w300, h300 = img300.width, img300.height

    # 300 DPI should be exactly 2x 150 DPI dimensions
    assert abs(w300 - 2 * w150) <= 2
    assert abs(h300 - 2 * h150) <= 2


@pytest.mark.asyncio
async def test_pdf_to_jpg_custom_output_filename(tmp_path):
    handler = PdfToJpgPDFHandler()
    pdf_bytes = create_sample_pdf(2)
    in_file = tmp_path / "doc.pdf"
    in_file.write_bytes(pdf_bytes)

    # Without .zip suffix in config
    ctx = make_context(
        str(tmp_path),
        [{"original_name": "doc.pdf", "local_path": str(in_file)}],
        config={"output_filename": "archived_photos"},
    )
    res = await handler.process(ctx)
    assert res["filename"] == "archived_photos.zip"


@pytest.mark.asyncio
async def test_pdf_to_jpg_encrypted_pdf_rejected(tmp_path):
    handler = PdfToJpgPDFHandler()
    enc_bytes = create_encrypted_pdf("secret")
    in_file = tmp_path / "protected.pdf"
    in_file.write_bytes(enc_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "protected.pdf", "local_path": str(in_file)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "PDF_ENCRYPTED"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_pdf_to_jpg_corrupted_pdf_rejected(tmp_path):
    handler = PdfToJpgPDFHandler()
    in_file = tmp_path / "corrupted.pdf"
    in_file.write_bytes(b"%PDF-1.4\ncorrupted garbage stream%%EOF")

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "corrupted.pdf", "local_path": str(in_file)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "INVALID_PDF"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_pdf_to_jpg_empty_file_rejected(tmp_path):
    handler = PdfToJpgPDFHandler()
    in_file = tmp_path / "empty.pdf"
    in_file.write_bytes(b"")

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "empty.pdf", "local_path": str(in_file)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "EMPTY_FILE"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_pdf_to_jpg_invalid_config(tmp_path):
    handler = PdfToJpgPDFHandler()

    # dpi too low
    with pytest.raises(AppException) as exc_info:
        handler.validate_config({"dpi": 50})
    assert exc_info.value.code == "INVALID_CONFIG"

    # dpi too high
    with pytest.raises(AppException) as exc_info:
        handler.validate_config({"dpi": 800})
    assert exc_info.value.code == "INVALID_CONFIG"

    # invalid quality
    with pytest.raises(AppException) as exc_info:
        handler.validate_config({"quality": 120})
    assert exc_info.value.code == "INVALID_CONFIG"


@pytest.mark.asyncio
async def test_pdf_to_jpg_multi_file_rejected(tmp_path):
    handler = PdfToJpgPDFHandler()
    f1 = tmp_path / "f1.pdf"
    f2 = tmp_path / "f2.pdf"
    f1.write_bytes(b"%PDF-1.4")
    f2.write_bytes(b"%PDF-1.4")

    ctx = make_context(
        str(tmp_path),
        [
            {"original_name": "f1.pdf", "local_path": str(f1)},
            {"original_name": "f2.pdf", "local_path": str(f2)},
        ],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "INVALID_INPUT_COUNT"


@pytest.mark.asyncio
async def test_pdf_to_jpg_oversized_file_rejected(tmp_path, monkeypatch):
    from app.core.config import settings
    # Set limit to 1 MB for testing without allocating real large files
    monkeypatch.setattr(settings, "PDF_TO_JPG_MAX_FILE_SIZE_MB", 1)

    handler = PdfToJpgPDFHandler()
    in_file = tmp_path / "large.pdf"
    # Write 1.2 MB file
    in_file.write_bytes(b"%PDF-1.4\n" + b"0" * (1200 * 1024))

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "large.pdf", "local_path": str(in_file)}],
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "FILE_TOO_LARGE"
    assert exc_info.value.status_code == 413
    assert "exceeds maximum allowed size of 1 MB" in exc_info.value.message


@pytest.mark.asyncio
async def test_pdf_to_jpg_excessive_page_count_default_dpi(tmp_path, monkeypatch):
    # Sensible default limit is 100 pages. Test with 101 lightweight blank pages (~15KB)
    handler = PdfToJpgPDFHandler()
    pdf_bytes = create_sample_pdf(101)
    in_file = tmp_path / "book_101pages.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "book_101pages.pdf", "local_path": str(in_file)}],
        config={"dpi": 150},
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "EXCESSIVE_PAGE_COUNT"
    assert exc_info.value.status_code == 400
    assert "101 pages" in exc_info.value.message
    assert "limit of 100 pages" in exc_info.value.message


@pytest.mark.asyncio
async def test_pdf_to_jpg_excessive_page_count_300_dpi(tmp_path, monkeypatch):
    # 300 DPI high resolution limit is 50 pages. Test with 51 lightweight blank pages (~8KB)
    handler = PdfToJpgPDFHandler()
    pdf_bytes = create_sample_pdf(51)
    in_file = tmp_path / "gallery_51pages.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "gallery_51pages.pdf", "local_path": str(in_file)}],
        config={"dpi": 300},
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "EXCESSIVE_PAGE_COUNT"
    assert exc_info.value.status_code == 400
    assert "51 pages" in exc_info.value.message
    assert "limit of 50 pages for 300 DPI" in exc_info.value.message


@pytest.mark.asyncio
async def test_pdf_to_jpg_excessive_page_dimensions(tmp_path, monkeypatch):
    # Create a 1-page PDF with massive dimensions (e.g. 3000 x 3000 pt)
    # At 300 DPI: scale = 300/72 = 4.1667 -> 12,500 x 12,500 px > 8000 px limit
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=3000, height=3000)
    bio = io.BytesIO()
    writer.write(bio)

    handler = PdfToJpgPDFHandler()
    in_file = tmp_path / "huge_blueprint.pdf"
    in_file.write_bytes(bio.getvalue())

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "huge_blueprint.pdf", "local_path": str(in_file)}],
        config={"dpi": 300},
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "PAGE_DIMENSIONS_TOO_LARGE"
    assert exc_info.value.status_code == 400
    assert "exceed the maximum allowed rendering limits" in exc_info.value.message


@pytest.mark.asyncio
async def test_pdf_to_jpg_cleanup_after_failure(tmp_path, monkeypatch):
    """Verifies that resources are released and temp files can be deleted without Windows file lock errors."""
    import shutil
    temp_work_dir = tmp_path / "worker_sub_dir"
    temp_work_dir.mkdir()

    # Create oversized dimension page that fails on page 2
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=300)   # Page 1: normal
    writer.add_blank_page(width=4000, height=4000) # Page 2: excessive (> 8000px at 300 DPI)
    bio = io.BytesIO()
    writer.write(bio)

    in_file = temp_work_dir / "two_pages.pdf"
    in_file.write_bytes(bio.getvalue())

    handler = PdfToJpgPDFHandler()
    ctx = make_context(
        str(temp_work_dir),
        [{"original_name": "two_pages.pdf", "local_path": str(in_file)}],
        config={"dpi": 300},
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "PAGE_DIMENSIONS_TOO_LARGE"

    # Crucial assertion: ensure temp_work_dir and all contained files can be removed immediately
    # If any file or C++ handle was left open, rmtree would raise PermissionError (WinError 32)
    shutil.rmtree(temp_work_dir)
    assert not temp_work_dir.exists()


@pytest.mark.asyncio
async def test_pdf_to_jpg_aggregate_output_limit_exceeded(tmp_path, monkeypatch):
    from app.core.config import settings
    # Set limit to 0.001 MB (~1 KB) using monkeypatch to test without large files
    # Each page JPEG is ~1-2 KB minimum, so page 2 or page 1 will exceed this threshold
    monkeypatch.setattr(settings, "PDF_TO_JPG_MAX_AGGREGATE_OUTPUT_MB", 0.001)

    pdf_bytes = create_sample_pdf(3)
    in_file = tmp_path / "sample_3p.pdf"
    in_file.write_bytes(pdf_bytes)

    handler = PdfToJpgPDFHandler()
    ctx = make_context(
        str(tmp_path),
        [{"original_name": "sample_3p.pdf", "local_path": str(in_file)}],
        config={"dpi": 150},
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "OUTPUT_SIZE_LIMIT_EXCEEDED"
    assert exc_info.value.status_code == 413
    assert "Aggregate generated output size exceeded maximum allowed limit" in exc_info.value.message


@pytest.mark.asyncio
async def test_pdf_to_jpg_cleanup_after_aggregate_limit_reached(tmp_path, monkeypatch):
    """Verifies that when aggregate limit is reached mid-stream, partial output files are removed and directory is clean."""
    import shutil

    from app.core.config import settings

    temp_work_dir = tmp_path / "work_cleanup_dir"
    temp_work_dir.mkdir()

    # Set small limit so page 2 triggers the limit
    monkeypatch.setattr(settings, "PDF_TO_JPG_MAX_AGGREGATE_OUTPUT_MB", 0.003)

    pdf_bytes = create_sample_pdf(3)
    in_file = temp_work_dir / "sample_multi.pdf"
    in_file.write_bytes(pdf_bytes)

    handler = PdfToJpgPDFHandler()
    ctx = make_context(
        str(temp_work_dir),
        [{"original_name": "sample_multi.pdf", "local_path": str(in_file)}],
        config={"dpi": 150},
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(ctx)
    assert exc_info.value.code == "OUTPUT_SIZE_LIMIT_EXCEEDED"

    # Verify partial output.zip was cleaned up
    partial_zip = temp_work_dir / "output.zip"
    assert not partial_zip.exists(), "Partially generated output.zip should be deleted upon abort"

    # Verify temp directory can be unlinked with zero locked file handles
    shutil.rmtree(temp_work_dir)
    assert not temp_work_dir.exists()


