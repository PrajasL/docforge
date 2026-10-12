import io
import os
import tempfile
import zipfile

import pypdf
import pytest

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.split import SplitPDFHandler


def create_test_pdf(page_count: int = 1, start_width: float = 100, password: str = None) -> bytes:
    """Helper to generate an in-memory PDF with specified pages, increasing widths, and optional encryption."""
    writer = pypdf.PdfWriter()
    for i in range(page_count):
        writer.add_blank_page(width=start_width + i * 10, height=start_width + i * 10)
    if password:
        writer.encrypt(password)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_split_handler_custom_ranges():
    handler = SplitPDFHandler()
    pdf_bytes = create_test_pdf(page_count=5, start_width=100)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.pdf")
        with open(input_path, "wb") as f:
            f.write(pdf_bytes)

        progress_reports = []

        async def track_progress(p: int):
            progress_reports.append(p)

        context = ProcessingContext(
            job_id="test-job-split-ranges",
            input_files=[{"id": "file-1", "original_name": "input.pdf", "local_path": input_path}],
            config={
                "mode": "ranges",
                "ranges": "1-2, 3-5",
                "output_filename": "extracted_ranges.zip",
            },
            temp_dir=temp_dir,
            progress_callback=track_progress,
        )

        result = await handler.process(context)

        assert result["filename"] == "extracted_ranges.zip"
        assert result["content_type"] == "application/zip"
        assert result["file_count"] == 2
        assert result["size_bytes"] > 0
        assert os.path.exists(result["output_path"])
        assert len(progress_reports) == 2

        # Inspect ZIP contents
        with zipfile.ZipFile(result["output_path"], "r") as zf:
            namelist = zf.namelist()
            assert "range_1-2.pdf" in namelist
            assert "range_3-5.pdf" in namelist

            # Check range_1-2.pdf (2 pages: widths 100, 110)
            r1 = pypdf.PdfReader(io.BytesIO(zf.read("range_1-2.pdf")))
            assert len(r1.pages) == 2
            assert r1.pages[0].mediabox.width == 100
            assert r1.pages[1].mediabox.width == 110

            # Check range_3-5.pdf (3 pages: widths 120, 130, 140)
            r2 = pypdf.PdfReader(io.BytesIO(zf.read("range_3-5.pdf")))
            assert len(r2.pages) == 3
            assert r2.pages[0].mediabox.width == 120
            assert r2.pages[1].mediabox.width == 130
            assert r2.pages[2].mediabox.width == 140


@pytest.mark.asyncio
async def test_split_handler_every_page_mode():
    handler = SplitPDFHandler()
    pdf_bytes = create_test_pdf(page_count=3, start_width=150)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.pdf")
        with open(input_path, "wb") as f:
            f.write(pdf_bytes)

        context = ProcessingContext(
            job_id="test-job-every-page",
            input_files=[{"id": "file-1", "original_name": "input.pdf", "local_path": input_path}],
            config={"mode": "every_page"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        result = await handler.process(context)

        assert result["filename"] == "split_documents.zip"
        assert result["file_count"] == 3

        with zipfile.ZipFile(result["output_path"], "r") as zf:
            files = sorted(zf.namelist())
            assert len(files) == 3
            assert files == ["page_01.pdf", "page_02.pdf", "page_03.pdf"]

            for idx, fname in enumerate(files):
                r = pypdf.PdfReader(io.BytesIO(zf.read(fname)))
                assert len(r.pages) == 1
                assert r.pages[0].mediabox.width == 150 + idx * 10


@pytest.mark.asyncio
async def test_split_handler_single_page_pdf():
    handler = SplitPDFHandler()
    pdf_bytes = create_test_pdf(page_count=1, start_width=200)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "single.pdf")
        with open(input_path, "wb") as f:
            f.write(pdf_bytes)

        context = ProcessingContext(
            job_id="test-job-single",
            input_files=[{"id": "file-1", "original_name": "single.pdf", "local_path": input_path}],
            config={"mode": "ranges", "ranges": "1"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )

        result = await handler.process(context)
        assert result["file_count"] == 1

        with zipfile.ZipFile(result["output_path"], "r") as zf:
            namelist = zf.namelist()
            assert "page_1.pdf" in namelist
            r = pypdf.PdfReader(io.BytesIO(zf.read("page_1.pdf")))
            assert len(r.pages) == 1
            assert r.pages[0].mediabox.width == 200


@pytest.mark.asyncio
async def test_split_handler_invalid_ranges():
    handler = SplitPDFHandler()
    pdf_bytes = create_test_pdf(page_count=5)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.pdf")
        with open(input_path, "wb") as f:
            f.write(pdf_bytes)

        # 1. Start page greater than end page: "4-2"
        context_inverted = ProcessingContext(
            job_id="test-job-inv",
            input_files=[{"id": "file-1", "original_name": "input.pdf", "local_path": input_path}],
            config={"mode": "ranges", "ranges": "4-2"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc1:
            await handler.process(context_inverted)
        assert exc1.value.code == "INVALID_PAGE_RANGE"

        # 2. Out of bounds range: "1-10" on 5-page document
        context_oob = ProcessingContext(
            job_id="test-job-oob",
            input_files=[{"id": "file-1", "original_name": "input.pdf", "local_path": input_path}],
            config={"mode": "ranges", "ranges": "1-10"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc2:
            await handler.process(context_oob)
        assert exc2.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"

        # 3. Page index 0
        context_zero = ProcessingContext(
            job_id="test-job-zero",
            input_files=[{"id": "file-1", "original_name": "input.pdf", "local_path": input_path}],
            config={"mode": "ranges", "ranges": "0-3"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc3:
            await handler.process(context_zero)
        assert exc3.value.code == "PAGE_RANGE_OUT_OF_BOUNDS"

        # 4. Non-integer characters
        context_alpha = ProcessingContext(
            job_id="test-job-alpha",
            input_files=[{"id": "file-1", "original_name": "input.pdf", "local_path": input_path}],
            config={"mode": "ranges", "ranges": "1-abc"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc4:
            await handler.process(context_alpha)
        assert exc4.value.code == "INVALID_PAGE_RANGE"


@pytest.mark.asyncio
async def test_split_handler_invalid_files():
    handler = SplitPDFHandler()

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Multiple files rejected (Split only accepts 1)
        p1 = os.path.join(temp_dir, "f1.pdf")
        p2 = os.path.join(temp_dir, "f2.pdf")
        with open(p1, "wb") as f:
            f.write(create_test_pdf(1))
        with open(p2, "wb") as f:
            f.write(create_test_pdf(1))

        context_multi = ProcessingContext(
            job_id="test-job-multi",
            input_files=[
                {"id": "f1", "original_name": "f1.pdf", "local_path": p1},
                {"id": "f2", "original_name": "f2.pdf", "local_path": p2},
            ],
            config={"mode": "every_page"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc1:
            await handler.process(context_multi)
        assert exc1.value.code == "INVALID_FILE_COUNT"

        # 2. Corrupted file rejected
        p_corrupt = os.path.join(temp_dir, "corrupt.pdf")
        with open(p_corrupt, "wb") as f:
            f.write(b"%PDF-1.4\ncorrupted garbage file content")

        context_corrupt = ProcessingContext(
            job_id="test-job-corrupt",
            input_files=[{"id": "f1", "original_name": "corrupt.pdf", "local_path": p_corrupt}],
            config={"mode": "every_page"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc2:
            await handler.process(context_corrupt)
        assert exc2.value.code == "CORRUPTED_PDF"

        # 3. Encrypted file rejected
        p_enc = os.path.join(temp_dir, "enc.pdf")
        with open(p_enc, "wb") as f:
            f.write(create_test_pdf(2, password="secret"))

        context_enc = ProcessingContext(
            job_id="test-job-enc",
            input_files=[{"id": "f1", "original_name": "enc.pdf", "local_path": p_enc}],
            config={"mode": "every_page"},
            temp_dir=temp_dir,
            progress_callback=lambda p: None,
        )
        with pytest.raises(AppException) as exc3:
            await handler.process(context_enc)
        assert exc3.value.code == "PDF_ENCRYPTED"
