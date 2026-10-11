import io
import os
import pytest
import pypdf
from app.core.errors import AppException
from app.tools.extract_pages import ExtractPagesPDFHandler, parse_extract_pages
from app.tools.base import ProcessingContext


def create_sample_pdf(page_count: int = 5, rotated_pages: dict = None) -> bytes:
    """Creates a sample multi-page PDF with varying dimensions and rotations."""
    rotated_pages = rotated_pages or {}
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        width = 200 + (i * 50)
        height = 300 + (i * 50)
        page = pypdf.PageObject.create_blank_page(width=width, height=height)
        if i + 1 in rotated_pages:
            page.rotate(rotated_pages[i + 1])
        writer.add_page(page)
    writer.add_metadata({"/Title": "Multi-Page Test Document", "/Author": "DocForge"})
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
        job_id="test-job-extract",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


def test_parse_extract_pages_helper():
    # 1. Single pages
    assert parse_extract_pages("1, 3, 5", total_pages=5) == [0, 2, 4]

    # 2. Page ranges
    assert parse_extract_pages("2-4", total_pages=5) == [1, 2, 3]

    # 3. Mixed ranges and single pages
    assert parse_extract_pages("1, 3-5", total_pages=5) == [0, 2, 3, 4]

    # 4. Custom ordering
    assert parse_extract_pages("5, 1, 3", total_pages=5) == [4, 0, 2]

    # 5. Overlapping / duplicates
    assert parse_extract_pages("2, 2-3", total_pages=5) == [1, 1, 2]

    # 6. Extract all
    assert parse_extract_pages("all", total_pages=4) == [0, 1, 2, 3]
    assert parse_extract_pages("", total_pages=4, extract_all=True) == [0, 1, 2, 3]


def test_parse_extract_pages_validation_errors():
    # Out of bounds
    with pytest.raises(AppException) as exc1:
        parse_extract_pages("6", total_pages=5)
    assert exc1.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"

    with pytest.raises(AppException) as exc2:
        parse_extract_pages("2-7", total_pages=5)
    assert exc2.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"

    # Start > end
    with pytest.raises(AppException) as exc3:
        parse_extract_pages("4-2", total_pages=5)
    assert exc3.value.code == "INVALID_PAGE_RANGE"

    # Invalid syntax
    with pytest.raises(AppException) as exc4:
        parse_extract_pages("abc", total_pages=5)
    assert exc4.value.code == "INVALID_PAGE_RANGE"

    # Zero or negative
    with pytest.raises(AppException) as exc5:
        parse_extract_pages("0-3", total_pages=5)
    assert exc5.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"


@pytest.mark.asyncio
async def test_extract_pages_custom_order_and_properties(tmp_path):
    handler = ExtractPagesPDFHandler()
    pdf_bytes = create_sample_pdf(page_count=5, rotated_pages={2: 90, 4: 180})
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    # Extract pages 4, 2, 1 in that specific non-sequential order
    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "pages": "4, 2, 1",
            "output_filename": "reordered_extract.pdf",
        },
    )
    result = await handler.process(ctx)

    assert os.path.exists(result["local_path"])
    assert result["filename"] == "reordered_extract.pdf"
    assert result["page_count"] == 3

    # Verify extracted PDF structure with pypdf
    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 3

    # Page 1 in output was Page 4 in original (width: 350, height: 450, rot: 180)
    p0 = reader.pages[0]
    assert float(p0.mediabox.width) == 350.0
    assert float(p0.mediabox.height) == 450.0
    assert p0.rotation == 180

    # Page 2 in output was Page 2 in original (width: 250, height: 350, rot: 90)
    p1 = reader.pages[1]
    assert float(p1.mediabox.width) == 250.0
    assert float(p1.mediabox.height) == 350.0
    assert p1.rotation == 90

    # Page 3 in output was Page 1 in original (width: 200, height: 300, rot: 0)
    p2 = reader.pages[2]
    assert float(p2.mediabox.width) == 200.0
    assert float(p2.mediabox.height) == 300.0
    assert p2.rotation == 0


@pytest.mark.asyncio
async def test_extract_pages_multiple_ranges_and_duplicates(tmp_path):
    handler = ExtractPagesPDFHandler()
    pdf_bytes = create_sample_pdf(page_count=5)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    # Extract "1-2, 2, 4-5" -> 5 pages total [0, 1, 1, 3, 4]
    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={"pages": "1-2, 2, 4-5"},
    )
    result = await handler.process(ctx)
    assert result["filename"] == "extracted_sample.pdf"
    assert result["page_count"] == 5

    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 5


@pytest.mark.asyncio
async def test_extract_all_pages_mode(tmp_path):
    handler = ExtractPagesPDFHandler()
    pdf_bytes = create_sample_pdf(page_count=4)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={"extract_all": True},
    )
    result = await handler.process(ctx)
    assert result["page_count"] == 4

    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 4


@pytest.mark.asyncio
async def test_extract_pages_encrypted_rejection(tmp_path):
    handler = ExtractPagesPDFHandler()
    enc_bytes = create_encrypted_pdf()
    in_file = tmp_path / "locked.pdf"
    in_file.write_bytes(enc_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "locked.pdf", "local_path": str(in_file)}],
        config={"pages": "1"},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "ENCRYPTED_FILE"


@pytest.mark.asyncio
async def test_extract_pages_corrupted_and_empty_files(tmp_path):
    handler = ExtractPagesPDFHandler()

    # Empty file
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    ctx_empty = make_context(
        str(tmp_path), [{"original_name": "empty.pdf", "local_path": str(empty_file)}], {"pages": "1"}
    )
    with pytest.raises(AppException) as exc1:
        await handler.process(ctx_empty)
    assert exc1.value.code == "EMPTY_INPUT_FILE"

    # Corrupted file
    corrupt_file = tmp_path / "bad.pdf"
    corrupt_file.write_bytes(b"%PDF-1.4\nCorrupted content without xref or pages")
    ctx_bad = make_context(
        str(tmp_path), [{"original_name": "bad.pdf", "local_path": str(corrupt_file)}], {"pages": "1"}
    )
    with pytest.raises(AppException) as exc2:
        await handler.process(ctx_bad)
    assert exc2.value.code == "CORRUPTED_FILE"


@pytest.mark.asyncio
async def test_extract_pages_metadata_preservation(tmp_path):
    handler = ExtractPagesPDFHandler()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_blank_page(width=300, height=400)
    metadata = {
        "/Title": "Confidential Extract Test",
        "/Author": "DocForge Engineer",
        "/Subject": "Testing Metadata Preservation",
        "/Creator": "DocForge Test Runner",
    }
    writer.add_metadata(metadata)
    in_file = tmp_path / "meta_source.pdf"
    with open(in_file, "wb") as f:
        writer.write(f)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "meta_source.pdf", "local_path": str(in_file)}],
        {"pages": "1"},
    )
    result = await handler.process(ctx)

    assert os.path.exists(result["local_path"])
    reader = pypdf.PdfReader(result["local_path"])
    assert reader.metadata is not None
    assert reader.metadata.title == "Confidential Extract Test"
    assert reader.metadata.author == "DocForge Engineer"
    assert reader.metadata.subject == "Testing Metadata Preservation"
    assert reader.metadata.creator == "DocForge Test Runner"
