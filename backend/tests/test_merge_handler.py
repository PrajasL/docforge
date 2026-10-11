import io
import os
import tempfile
import pytest
import pypdf

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.merge import MergePDFHandler


def create_test_pdf(page_count: int = 1, width: float = 100, height: float = 100, password: str = None) -> bytes:
    """Helper to generate an in-memory PDF with specified pages, dimensions, and optional encryption."""
    writer = pypdf.PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=width, height=height)
    if password:
        writer.encrypt(password)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_merge_handler_success():
    handler = MergePDFHandler()

    pdf1_bytes = create_test_pdf(page_count=2, width=150, height=150)
    pdf2_bytes = create_test_pdf(page_count=3, width=250, height=250)

    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "doc1.pdf")
        p2 = os.path.join(temp_dir, "doc2.pdf")

        with open(p1, "wb") as f:
            f.write(pdf1_bytes)
        with open(p2, "wb") as f:
            f.write(pdf2_bytes)

        progress_reports = []

        async def track_progress(p: int):
            progress_reports.append(p)

        context = ProcessingContext(
            job_id="test-job-123",
            input_files=[
                {"id": "file-1", "original_name": "doc1.pdf", "local_path": p1},
                {"id": "file-2", "original_name": "doc2.pdf", "local_path": p2},
            ],
            config={"output_filename": "final_merged.pdf"},
            temp_dir=temp_dir,
            progress_callback=track_progress,
        )

        result = await handler.process(context)

        assert result["filename"] == "final_merged.pdf"
        assert result["page_count"] == 5
        assert result["size_bytes"] > 0
        assert os.path.exists(result["output_path"])
        assert len(progress_reports) == 2
        assert progress_reports[-1] >= 80

        # Verify output is a valid readable PDF with 5 pages and preserved dimensions
        with open(result["output_path"], "rb") as out_f:
            reader = pypdf.PdfReader(out_f)
            assert len(reader.pages) == 5
            # First 2 pages are 150x150, next 3 pages are 250x250
            assert reader.pages[0].mediabox.width == 150
            assert reader.pages[1].mediabox.width == 150
            assert reader.pages[2].mediabox.width == 250
            assert reader.pages[3].mediabox.width == 250
            assert reader.pages[4].mediabox.width == 250


@pytest.mark.asyncio
async def test_merge_handler_custom_order():
    handler = MergePDFHandler()

    # doc1 has width 100, doc2 has width 300
    pdf1_bytes = create_test_pdf(page_count=1, width=100, height=100)
    pdf2_bytes = create_test_pdf(page_count=1, width=300, height=300)

    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "doc1.pdf")
        p2 = os.path.join(temp_dir, "doc2.pdf")

        with open(p1, "wb") as f:
            f.write(pdf1_bytes)
        with open(p2, "wb") as f:
            f.write(pdf2_bytes)

        # Invert order in config: file-2 first, then file-1
        context = ProcessingContext(
            job_id="test-job-order",
            input_files=[
                {"id": "file-1", "original_name": "doc1.pdf", "local_path": p1},
                {"id": "file-2", "original_name": "doc2.pdf", "local_path": p2},
            ],
            config={"file_order": ["file-2", "file-1"]},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        result = await handler.process(context)
        with open(result["output_path"], "rb") as out_f:
            reader = pypdf.PdfReader(out_f)
            assert len(reader.pages) == 2
            # Page 0 should be doc2 (width 300), page 1 should be doc1 (width 100)
            assert reader.pages[0].mediabox.width == 300
            assert reader.pages[1].mediabox.width == 100


@pytest.mark.asyncio
async def test_merge_handler_insufficient_files():
    handler = MergePDFHandler()

    with tempfile.TemporaryDirectory() as temp_dir:
        context = ProcessingContext(
            job_id="test-job-insufficient",
            input_files=[{"id": "file-1", "original_name": "doc1.pdf", "local_path": "/fake/path"}],
            config={},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        with pytest.raises(AppException) as exc_info:
            await handler.process(context)
        assert exc_info.value.code == "INSUFFICIENT_FILES"


@pytest.mark.asyncio
async def test_merge_handler_too_many_files():
    handler = MergePDFHandler()

    files = [{"id": f"file-{i}", "original_name": f"doc{i}.pdf", "local_path": f"/fake/{i}"} for i in range(25)]
    with tempfile.TemporaryDirectory() as temp_dir:
        context = ProcessingContext(
            job_id="test-job-too-many",
            input_files=files,
            config={},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        with pytest.raises(AppException) as exc_info:
            await handler.process(context)
        assert exc_info.value.code == "TOO_MANY_FILES"


@pytest.mark.asyncio
async def test_merge_handler_empty_file():
    handler = MergePDFHandler()

    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "doc1.pdf")
        p2 = os.path.join(temp_dir, "empty.pdf")

        with open(p1, "wb") as f:
            f.write(create_test_pdf(page_count=1))
        with open(p2, "wb") as f:
            pass  # 0 bytes

        context = ProcessingContext(
            job_id="test-job-empty",
            input_files=[
                {"id": "file-1", "original_name": "doc1.pdf", "local_path": p1},
                {"id": "file-2", "original_name": "empty.pdf", "local_path": p2},
            ],
            config={},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        with pytest.raises(AppException) as exc_info:
            await handler.process(context)
        assert exc_info.value.code == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_merge_handler_corrupted_file():
    handler = MergePDFHandler()

    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "doc1.pdf")
        p2 = os.path.join(temp_dir, "corrupted.pdf")

        with open(p1, "wb") as f:
            f.write(create_test_pdf(page_count=1))
        with open(p2, "wb") as f:
            f.write(b"%PDF-1.4\ncorrupted content without pdf structure")

        context = ProcessingContext(
            job_id="test-job-corrupt",
            input_files=[
                {"id": "file-1", "original_name": "doc1.pdf", "local_path": p1},
                {"id": "file-2", "original_name": "corrupted.pdf", "local_path": p2},
            ],
            config={},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        with pytest.raises(AppException) as exc_info:
            await handler.process(context)
        assert exc_info.value.code == "CORRUPTED_PDF"


@pytest.mark.asyncio
async def test_merge_handler_encrypted_file():
    handler = MergePDFHandler()

    with tempfile.TemporaryDirectory() as temp_dir:
        p1 = os.path.join(temp_dir, "doc1.pdf")
        p2 = os.path.join(temp_dir, "encrypted.pdf")

        with open(p1, "wb") as f:
            f.write(create_test_pdf(page_count=1))
        with open(p2, "wb") as f:
            f.write(create_test_pdf(page_count=1, password="secret_pass"))

        context = ProcessingContext(
            job_id="test-job-encrypted",
            input_files=[
                {"id": "file-1", "original_name": "doc1.pdf", "local_path": p1},
                {"id": "file-2", "original_name": "encrypted.pdf", "local_path": p2},
            ],
            config={},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        with pytest.raises(AppException) as exc_info:
            await handler.process(context)
        assert exc_info.value.code == "PDF_ENCRYPTED"
