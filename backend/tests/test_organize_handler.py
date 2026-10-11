import io
import os
import pytest
import pypdf
from app.core.errors import AppException
from app.tools.organize import OrganizePDFHandler, normalize_organize_pages
from app.tools.base import ProcessingContext


def create_sample_pdf(page_count: int = 5, rotated_pages: dict = None) -> bytes:
    """Creates a sample multi-page PDF with custom dimensions, rotations, and metadata."""
    rotated_pages = rotated_pages or {}
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        width = 200 + (i * 50)
        height = 300 + (i * 50)
        page = pypdf.PageObject.create_blank_page(width=width, height=height)
        if i + 1 in rotated_pages:
            page.rotate(rotated_pages[i + 1])
        writer.add_page(page)
    writer.add_metadata({
        "/Title": "Organize PDF Sample",
        "/Author": "DocForge Test",
        "/Subject": "Testing Page Reordering and Manipulation",
    })
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
        job_id="test-job-organize",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


def test_normalize_organize_pages_valid():
    # 1. Dict format with rotations
    spec_dict = [
        {"page_number": 3, "rotation": 90},
        {"page": 1, "rotation": 180},
        {"page_number": 2, "rotation": 0},
    ]
    res1 = normalize_organize_pages(spec_dict, total_pages=5)
    assert res1 == [
        {"page_number": 3, "rotation": 90},
        {"page_number": 1, "rotation": 180},
        {"page_number": 2, "rotation": 0},
    ]

    # 2. Integer list format
    spec_ints = [4, 2, 5]
    res2 = normalize_organize_pages(spec_ints, total_pages=5)
    assert res2 == [
        {"page_number": 4, "rotation": 0},
        {"page_number": 2, "rotation": 0},
        {"page_number": 5, "rotation": 0},
    ]

    # 3. Comma-separated string format
    res3 = normalize_organize_pages("2, 1, 3", total_pages=5)
    assert res3 == [
        {"page_number": 2, "rotation": 0},
        {"page_number": 1, "rotation": 0},
        {"page_number": 3, "rotation": 0},
    ]

    # 4. Duplicated pages
    res4 = normalize_organize_pages([{"page_number": 1, "rotation": 0}, {"page_number": 1, "rotation": 90}], total_pages=3)
    assert len(res4) == 2
    assert res4[0]["page_number"] == 1 and res4[0]["rotation"] == 0
    assert res4[1]["page_number"] == 1 and res4[1]["rotation"] == 90


def test_normalize_organize_pages_errors():
    # Empty
    with pytest.raises(AppException) as exc1:
        normalize_organize_pages([], total_pages=5)
    assert exc1.value.code == "INVALID_CONFIG"

    # Out of bounds high
    with pytest.raises(AppException) as exc2:
        normalize_organize_pages([6], total_pages=5)
    assert exc2.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"

    # Out of bounds low
    with pytest.raises(AppException) as exc3:
        normalize_organize_pages([0], total_pages=5)
    assert exc3.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"

    # Invalid rotation angle
    with pytest.raises(AppException) as exc4:
        normalize_organize_pages([{"page_number": 1, "rotation": 45}], total_pages=5)
    assert exc4.value.code == "INVALID_ROTATION_ANGLE"

    # Invalid page number type
    with pytest.raises(AppException) as exc5:
        normalize_organize_pages([{"page_number": "abc"}], total_pages=5)
    assert exc5.value.code == "INVALID_PAGE_NUMBER"


@pytest.mark.asyncio
async def test_organize_reordering_deletion_and_rotation(tmp_path):
    handler = OrganizePDFHandler()
    pdf_bytes = create_sample_pdf(page_count=5)
    in_file = tmp_path / "original.pdf"
    in_file.write_bytes(pdf_bytes)

    # Reorder (3, 1), delete (2, 4, 5), rotate page 3 by 90°
    ctx = make_context(
        str(tmp_path),
        [{"original_name": "original.pdf", "local_path": str(in_file)}],
        {
            "pages": [
                {"page_number": 3, "rotation": 90},
                {"page_number": 1, "rotation": 0},
            ],
            "output_filename": "reordered_final.pdf",
        },
    )
    result = await handler.process(ctx)

    assert os.path.exists(result["local_path"])
    assert result["filename"] == "reordered_final.pdf"
    assert result["page_count"] == 2

    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 2

    # Original page 3 was width=300, height=400, rotated +90
    p0 = reader.pages[0]
    assert float(p0.mediabox.width) == 300.0
    assert float(p0.mediabox.height) == 400.0
    assert p0.rotation == 90

    # Original page 1 was width=200, height=300, rotation 0
    p1 = reader.pages[1]
    assert float(p1.mediabox.width) == 200.0
    assert float(p1.mediabox.height) == 300.0
    assert p1.rotation == 0


@pytest.mark.asyncio
async def test_organize_page_duplication_with_different_rotations(tmp_path):
    handler = OrganizePDFHandler()
    pdf_bytes = create_sample_pdf(page_count=2)
    in_file = tmp_path / "two_pages.pdf"
    in_file.write_bytes(pdf_bytes)

    # Duplicate page 1 twice (one at 0°, one at 180°), duplicate page 2 once
    ctx = make_context(
        str(tmp_path),
        [{"original_name": "two_pages.pdf", "local_path": str(in_file)}],
        {
            "pages": [
                {"page_number": 1, "rotation": 0},
                {"page_number": 1, "rotation": 180},
                {"page_number": 2, "rotation": 270},
            ]
        },
    )
    result = await handler.process(ctx)
    assert result["page_count"] == 3

    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 3
    assert reader.pages[0].rotation == 0
    assert reader.pages[1].rotation == 180
    assert reader.pages[2].rotation == 270


@pytest.mark.asyncio
async def test_organize_preserves_metadata(tmp_path):
    handler = OrganizePDFHandler()
    pdf_bytes = create_sample_pdf(page_count=3)
    in_file = tmp_path / "metadata_test.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "metadata_test.pdf", "local_path": str(in_file)}],
        {"pages": [2, 1]},
    )
    result = await handler.process(ctx)

    reader = pypdf.PdfReader(result["local_path"])
    assert reader.metadata is not None
    assert reader.metadata.title == "Organize PDF Sample"
    assert reader.metadata.author == "DocForge Test"
    assert reader.metadata.subject == "Testing Page Reordering and Manipulation"


@pytest.mark.asyncio
async def test_organize_encrypted_file_fails(tmp_path):
    handler = OrganizePDFHandler()
    enc_bytes = create_encrypted_pdf()
    in_file = tmp_path / "locked.pdf"
    in_file.write_bytes(enc_bytes)

    ctx = make_context(
        str(tmp_path),
        [{"original_name": "locked.pdf", "local_path": str(in_file)}],
        {"pages": [1]},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "ENCRYPTED_FILE"


@pytest.mark.asyncio
async def test_organize_empty_and_corrupt_files(tmp_path):
    handler = OrganizePDFHandler()

    # Empty 0-byte file
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    ctx_empty = make_context(
        str(tmp_path),
        [{"original_name": "empty.pdf", "local_path": str(empty_file)}],
        {"pages": [1]},
    )
    with pytest.raises(AppException) as exc1:
        await handler.process(ctx_empty)
    assert exc1.value.code == "EMPTY_INPUT_FILE"

    # Corrupt file
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"%PDF-1.4\nNot a real pdf document content...")
    ctx_corrupt = make_context(
        str(tmp_path),
        [{"original_name": "corrupt.pdf", "local_path": str(corrupt_file)}],
        {"pages": [1]},
    )
    with pytest.raises(AppException) as exc2:
        await handler.process(ctx_corrupt)
    assert exc2.value.code == "CORRUPTED_FILE"
