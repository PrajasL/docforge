import io
import os
import shutil
import tempfile
import pytest
import pypdf

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.rotate import RotatePDFHandler, parse_page_selection


def create_sample_pdf(num_pages: int = 4, width: int = 612, height: int = 792) -> bytes:
    """Creates a simple multi-page PDF with varying page dimensions."""
    writer = pypdf.PdfWriter()
    for i in range(num_pages):
        writer.add_blank_page(width=width + i * 20, height=height + i * 30)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    """Helper to build ProcessingContext with dummy progress callback."""
    async def dummy_progress(p: int):
        pass

    return ProcessingContext(
        job_id="test-job-rotate",
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
async def test_rotate_all_pages_90_180_270(temp_workspace):
    """Verifies rotating all pages by 90, 180, and 270 degrees clockwise."""
    handler = RotatePDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=3)

    for angle in (90, 180, 270):
        sub_dir = os.path.join(temp_workspace, f"angle_{angle}")
        os.makedirs(sub_dir, exist_ok=True)
        input_path = os.path.join(sub_dir, "sample.pdf")
        with open(input_path, "wb") as f:
            f.write(pdf_bytes)

        context = make_context(
            temp_dir=sub_dir,
            input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
            config={"angle": angle, "pages": "all"},
        )

        result = await handler.process(context)

        assert os.path.exists(result["output_path"])
        assert result["page_count"] == 3
        assert result["rotated_pages_count"] == 3
        assert result["rotation_angle"] == angle
        assert result["content_type"] == "application/pdf"

        # Verify page rotations in output PDF
        reader = pypdf.PdfReader(result["output_path"])
        assert len(reader.pages) == 3
        for p in reader.pages:
            assert p.rotation == angle


@pytest.mark.asyncio
async def test_rotate_individual_pages(temp_workspace):
    """Verifies rotating specific individual pages and page ranges."""
    handler = RotatePDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=4)

    input_path = os.path.join(temp_workspace, "sample.pdf")
    with open(input_path, "wb") as f:
        f.write(pdf_bytes)

    # 1. Rotate pages 1 and 3 by 90°
    context = make_context(
        temp_dir=temp_workspace,
        input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
        config={"angle": 90, "pages": "1, 3"},
    )
    result = await handler.process(context)

    reader = pypdf.PdfReader(result["output_path"])
    assert len(reader.pages) == 4
    assert reader.pages[0].rotation == 90
    assert reader.pages[1].rotation == 0
    assert reader.pages[2].rotation == 90
    assert reader.pages[3].rotation == 0

    # 2. Rotate range "2-4" by 180°
    context2 = make_context(
        temp_dir=temp_workspace,
        input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
        config={"angle": 180, "pages": "2-4"},
    )
    res2 = await handler.process(context2)
    reader2 = pypdf.PdfReader(res2["output_path"])
    assert reader2.pages[0].rotation == 0
    assert reader2.pages[1].rotation == 180
    assert reader2.pages[2].rotation == 180
    assert reader2.pages[3].rotation == 180

    # 3. Custom page_rotations mapping: {"1": 90, "4": 270}
    context3 = make_context(
        temp_dir=temp_workspace,
        input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
        config={"page_rotations": {"1": 90, "4": 270}},
    )
    res3 = await handler.process(context3)
    reader3 = pypdf.PdfReader(res3["output_path"])
    assert reader3.pages[0].rotation == 90
    assert reader3.pages[1].rotation == 0
    assert reader3.pages[2].rotation == 0
    assert reader3.pages[3].rotation == 270


@pytest.mark.asyncio
async def test_rotate_invalid_angles(temp_workspace):
    """Verifies rejection of non-90-degree angles."""
    handler = RotatePDFHandler()

    with pytest.raises(AppException) as exc_info:
        handler.validate_config({"angle": 45})
    assert exc_info.value.code == "INVALID_ROTATION_ANGLE"

    with pytest.raises(AppException) as exc_info:
        handler.validate_config({"angle": "not_a_number"})
    assert exc_info.value.code == "INVALID_ROTATION_ANGLE"


@pytest.mark.asyncio
async def test_rotate_page_out_of_bounds(temp_workspace):
    """Verifies rejection of page selections beyond total page count."""
    handler = RotatePDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=3)

    input_path = os.path.join(temp_workspace, "sample.pdf")
    with open(input_path, "wb") as f:
        f.write(pdf_bytes)

    # Page 5 on 3-page document
    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
                config={"angle": 90, "pages": "5"},
            )
        )
    assert exc_info.value.code == "PAGE_NUMBER_OUT_OF_BOUNDS"

    # Start > end range
    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": input_path, "original_name": "sample.pdf"}],
                config={"angle": 90, "pages": "3-1"},
            )
        )
    assert exc_info.value.code == "INVALID_PAGE_RANGE"


@pytest.mark.asyncio
async def test_rotate_invalid_files(temp_workspace):
    """Verifies rejection of corrupted, encrypted, empty, and multiple files."""
    handler = RotatePDFHandler()

    # 1. Corrupted file
    corrupt_path = os.path.join(temp_workspace, "corrupt.pdf")
    with open(corrupt_path, "wb") as f:
        f.write(b"%PDF-1.4\ncorrupted junk bytes\xff\xfe")

    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": corrupt_path, "original_name": "corrupt.pdf"}],
                config={"angle": 90},
            )
        )
    assert exc_info.value.code == "CORRUPTED_PDF"

    # 2. Encrypted file
    enc_path = os.path.join(temp_workspace, "encrypted.pdf")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("pass123")
    with open(enc_path, "wb") as f:
        writer.write(f)

    with pytest.raises(AppException) as exc_info:
        await handler.process(
            make_context(
                temp_dir=temp_workspace,
                input_files=[{"local_path": enc_path, "original_name": "encrypted.pdf"}],
                config={"angle": 90},
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
                config={"angle": 90},
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
                config={"angle": 90},
            )
        )
    assert exc_info.value.code == "INVALID_FILE_COUNT"
