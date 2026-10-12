import io
import os

import pypdf
import pytest

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.page_numbers import PageNumbersPDFHandler, parse_hex_color


def create_dummy_pdf(num_pages: int = 3, width: float = 400, height: float = 600) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        page = pypdf.PageObject.create_blank_page(width=width, height=height)
        writer.add_page(page)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    async def dummy_progress(p: int):
        pass

    return ProcessingContext(
        job_id="test-job-page-numbers",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


def test_parse_hex_color():
    assert parse_hex_color("#000000") == (0.0, 0.0, 0.0)
    assert parse_hex_color("#FFFFFF") == (1.0, 1.0, 1.0)
    assert parse_hex_color("#fff") == (1.0, 1.0, 1.0)
    r, g, b = parse_hex_color("#374151")
    assert round(r, 2) == 0.22
    assert parse_hex_color("invalid") == (0.2, 0.2, 0.2)
    assert parse_hex_color("") == (0.2, 0.2, 0.2)


@pytest.mark.asyncio
async def test_page_numbers_positions_and_formats(tmp_path):
    handler = PageNumbersPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=3)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    # 1. Test bottom_center with page_n_of_total
    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "position": "bottom_center",
            "format": "page_n_of_total",
            "start_number": 1,
            "start_page": 1,
            "font_size": 12,
            "color": "#111827",
        },
    )
    result = await handler.process(ctx)
    assert os.path.exists(result["local_path"])
    assert result["page_count"] == 3
    assert result["numbered_pages_count"] == 3
    assert result["position"] == "bottom_center"
    assert result["numbering_format"] == "page_n_of_total"

    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 3
    assert "Page 1 of 3" in reader.pages[0].extract_text()
    assert "Page 2 of 3" in reader.pages[1].extract_text()
    assert "Page 3 of 3" in reader.pages[2].extract_text()

    # 2. Test top_right with format 'page_n'
    ctx2 = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "position": "top_right",
            "format": "page_n",
        },
    )
    res2 = await handler.process(ctx2)
    r2 = pypdf.PdfReader(res2["local_path"])
    assert "Page 1" in r2.pages[0].extract_text()

    # 3. Test bottom_left with format 'n'
    ctx3 = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "position": "bottom_left",
            "format": "n",
        },
    )
    res3 = await handler.process(ctx3)
    r3 = pypdf.PdfReader(res3["local_path"])
    assert "1" in r3.pages[0].extract_text()

    # 4. Test top_left with format 'n_of_total'
    ctx4 = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "position": "top_left",
            "format": "n_of_total",
        },
    )
    res4 = await handler.process(ctx4)
    r4 = pypdf.PdfReader(res4["local_path"])
    assert "1 of 3" in r4.pages[0].extract_text()


@pytest.mark.asyncio
async def test_page_numbers_start_page_and_start_number(tmp_path):
    handler = PageNumbersPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=4)
    in_file = tmp_path / "sample_4p.pdf"
    in_file.write_bytes(pdf_bytes)

    # Start page = 2, start number = 10, end page = 3
    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample_4p.pdf", "local_path": str(in_file)}],
        config={
            "position": "bottom_right",
            "format": "page_n_of_total",
            "start_page": 2,
            "start_number": 10,
            "end_page": 3,
            "output_filename": "custom_numbered.pdf",
        },
    )
    result = await handler.process(ctx)
    assert result["filename"] == "custom_numbered.pdf"
    assert result["page_count"] == 4
    assert result["numbered_pages_count"] == 2  # pages 2 and 3

    reader = pypdf.PdfReader(result["local_path"])
    # Page 1 (index 0) has NO numbering
    assert "Page" not in reader.pages[0].extract_text()
    # Page 2 (index 1) should be "Page 10 of 11"
    assert "Page 10 of 11" in reader.pages[1].extract_text()
    # Page 3 (index 2) should be "Page 11 of 11"
    assert "Page 11 of 11" in reader.pages[2].extract_text()
    # Page 4 (index 3) has NO numbering
    assert "Page" not in reader.pages[3].extract_text()


@pytest.mark.asyncio
async def test_page_numbers_mixed_sizes_and_rotations(tmp_path):
    """Verifies correct stamping on PDFs with varying page dimensions and rotations."""
    handler = PageNumbersPDFHandler()

    writer = pypdf.PdfWriter()
    # Page 1: Portrait Letter (612 x 792)
    p1 = pypdf.PageObject.create_blank_page(width=612, height=792)
    writer.add_page(p1)

    # Page 2: Landscape A4 (842 x 595)
    p2 = pypdf.PageObject.create_blank_page(width=842, height=595)
    writer.add_page(p2)

    # Page 3: Rotated 90 degrees
    p3 = pypdf.PageObject.create_blank_page(width=612, height=792)
    p3.rotate(90)
    writer.add_page(p3)

    in_file = tmp_path / "mixed.pdf"
    with open(in_file, "wb") as f:
        writer.write(f)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "mixed.pdf", "local_path": str(in_file)}],
        config={
            "position": "bottom_center",
            "format": "page_n_of_total",
            "margin": 25,
            "font_size": 14,
        },
    )
    result = await handler.process(ctx)
    assert result["page_count"] == 3
    assert result["numbered_pages_count"] == 3

    reader = pypdf.PdfReader(result["local_path"])
    assert "Page 1 of 3" in reader.pages[0].extract_text()
    assert "Page 2 of 3" in reader.pages[1].extract_text()
    assert "Page 3 of 3" in reader.pages[2].extract_text()

    # Verify Page 3 rotation was transferred to content (Rotate == 0 and dimensions swapped)
    assert reader.pages[2].get("/Rotate", 0) == 0
    assert float(reader.pages[2].mediabox.width) == 792.0
    assert float(reader.pages[2].mediabox.height) == 612.0


@pytest.mark.asyncio
async def test_page_numbers_validation_errors(tmp_path):
    handler = PageNumbersPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=2)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    # 1. Invalid position
    with pytest.raises(AppException) as exc1:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"position": "middle"}))
    assert exc1.value.code == "INVALID_CONFIG"
    assert "Invalid position" in exc1.value.message

    # 2. Invalid format
    with pytest.raises(AppException) as exc2:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"format": "roman"}))
    assert exc2.value.code == "INVALID_CONFIG"

    # 3. Invalid start_number (< 1)
    with pytest.raises(AppException) as exc3:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"start_number": 0}))
    assert exc3.value.code == "INVALID_CONFIG"

    # 4. Invalid start_page (< 1)
    with pytest.raises(AppException) as exc4:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"start_page": -1}))
    assert exc4.value.code == "INVALID_CONFIG"

    # 5. Invalid end_page < start_page
    with pytest.raises(AppException) as exc5:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"start_page": 2, "end_page": 1}))
    assert exc5.value.code == "INVALID_CONFIG"

    # 6. start_page > total pages
    with pytest.raises(AppException) as exc6:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"start_page": 10}))
    assert exc6.value.code == "PAGE_NUMBER_OUT_OF_BOUNDS"

    # 7. Font size out of range
    with pytest.raises(AppException) as exc7:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"font_size": 50}))
    assert exc7.value.code == "INVALID_CONFIG"

    # 8. Margin out of range
    with pytest.raises(AppException) as exc8:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"margin": 5}))
    assert exc8.value.code == "INVALID_CONFIG"


@pytest.mark.asyncio
async def test_page_numbers_corrupted_empty_encrypted_files(tmp_path):
    handler = PageNumbersPDFHandler()

    # 1. Missing file
    with pytest.raises(AppException) as exc1:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(tmp_path / "nonexistent.pdf")}]))
    assert exc1.value.code == "FILE_NOT_FOUND"

    # 2. Empty file (0 bytes)
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    with pytest.raises(AppException) as exc2:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(empty_file)}]))
    assert exc2.value.code == "EMPTY_INPUT_FILE"

    # 3. Corrupted file
    corrupt_file = tmp_path / "corrupted.pdf"
    corrupt_file.write_bytes(b"Not a real PDF file contents here")
    with pytest.raises(AppException) as exc3:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(corrupt_file)}]))
    assert exc3.value.code == "CORRUPTED_FILE"

    # 4. Encrypted file
    enc_writer = pypdf.PdfWriter()
    enc_writer.add_blank_page(width=300, height=300)
    enc_writer.encrypt("secure_password")
    enc_file = tmp_path / "encrypted.pdf"
    with open(enc_file, "wb") as f:
        enc_writer.write(f)

    with pytest.raises(AppException) as exc4:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(enc_file)}]))
    assert exc4.value.code == "DOCUMENT_ENCRYPTED"
