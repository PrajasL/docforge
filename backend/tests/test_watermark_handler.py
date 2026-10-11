import os
import io
import pytest
import pypdf
from app.core.errors import AppException
from app.tools.watermark import WatermarkPDFHandler
from app.tools.base import ProcessingContext


def create_dummy_pdf(num_pages: int = 3, width: float = 400, height: float = 600) -> bytes:
    writer = pypdf.PdfWriter()
    for i in range(num_pages):
        page = pypdf.PageObject.create_blank_page(width=width, height=height)
        writer.add_page(page)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    async def dummy_progress(p: int):
        pass

    return ProcessingContext(
        job_id="test-job-watermark",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


@pytest.mark.asyncio
async def test_watermark_text_positions_angles_opacity(tmp_path):
    handler = WatermarkPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=2)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    # 1. Diagonal watermark
    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "text": "CONFIDENTIAL",
            "position": "diagonal",
            "opacity": 0.4,
            "font_size": 36,
            "color": "#FF0000",
        },
    )
    result = await handler.process(ctx)
    assert os.path.exists(result["local_path"])
    assert result["page_count"] == 2
    assert result["watermarked_pages_count"] == 2
    assert result["watermark_text"] == "CONFIDENTIAL"

    # Verify text was written
    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 2
    for page in reader.pages:
        txt = page.extract_text()
        assert "CONFIDENTIAL" in txt

    # 2. Top watermark with custom angle
    ctx2 = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "text": "TOP SECRET",
            "position": "top",
            "angle": 0.0,
            "opacity": 0.5,
            "font_size": 24,
        },
    )
    result2 = await handler.process(ctx2)
    reader2 = pypdf.PdfReader(result2["local_path"])
    assert "TOP SECRET" in reader2.pages[0].extract_text()

    # 3. Bottom watermark
    ctx3 = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "text": "DO NOT COPY",
            "position": "bottom",
            "angle": 0.0,
        },
    )
    result3 = await handler.process(ctx3)
    reader3 = pypdf.PdfReader(result3["local_path"])
    assert "DO NOT COPY" in reader3.pages[0].extract_text()


@pytest.mark.asyncio
async def test_watermark_selective_pages(tmp_path):
    handler = WatermarkPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=4)
    in_file = tmp_path / "sample_4p.pdf"
    in_file.write_bytes(pdf_bytes)

    # Watermark only pages 1 and 3 (1-indexed)
    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample_4p.pdf", "local_path": str(in_file)}],
        config={
            "text": "INTERNAL ONLY",
            "pages": "1, 3",
            "position": "center",
        },
    )
    result = await handler.process(ctx)
    assert result["watermarked_pages_count"] == 2

    reader = pypdf.PdfReader(result["local_path"])
    assert len(reader.pages) == 4
    # Page 1 (index 0) has watermark
    assert "INTERNAL ONLY" in reader.pages[0].extract_text()
    # Page 2 (index 1) does NOT have watermark
    assert "INTERNAL ONLY" not in reader.pages[1].extract_text()
    # Page 3 (index 2) has watermark
    assert "INTERNAL ONLY" in reader.pages[2].extract_text()
    # Page 4 (index 3) does NOT have watermark
    assert "INTERNAL ONLY" not in reader.pages[3].extract_text()


@pytest.mark.asyncio
async def test_watermark_config_validation(tmp_path):
    handler = WatermarkPDFHandler()

    # Empty text
    with pytest.raises(AppException) as exc1:
        handler.validate_config({"text": "   "})
    assert exc1.value.code == "INVALID_CONFIG"

    # Excessively long text
    with pytest.raises(AppException) as exc2:
        handler.validate_config({"text": "A" * 201})
    assert exc2.value.code == "INVALID_CONFIG"

    # Opacity out of range
    with pytest.raises(AppException) as exc3:
        handler.validate_config({"opacity": 1.5})
    assert exc3.value.code == "INVALID_CONFIG"

    with pytest.raises(AppException) as exc4:
        handler.validate_config({"opacity": 0.01})
    assert exc4.value.code == "INVALID_CONFIG"

    # Font size out of range
    with pytest.raises(AppException) as exc5:
        handler.validate_config({"font_size": 200})
    assert exc5.value.code == "INVALID_CONFIG"

    with pytest.raises(AppException) as exc6:
        handler.validate_config({"font_size": 4})
    assert exc6.value.code == "INVALID_CONFIG"

    # Invalid position
    with pytest.raises(AppException) as exc7:
        handler.validate_config({"position": "sideways"})
    assert exc7.value.code == "INVALID_CONFIG"

    # Angle out of bounds
    with pytest.raises(AppException) as exc8:
        handler.validate_config({"angle": 500})
    assert exc8.value.code == "INVALID_CONFIG"


@pytest.mark.asyncio
async def test_watermark_corrupted_empty_encrypted_inputs(tmp_path):
    handler = WatermarkPDFHandler()

    # 1. 0-byte file
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    ctx_empty = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "empty.pdf", "local_path": str(empty_file)}],
        config={"text": "DRAFT"},
    )
    with pytest.raises(AppException) as exc_empty:
        await handler.process(ctx_empty)
    assert exc_empty.value.code == "EMPTY_INPUT_FILE"

    # 2. Corrupted file
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"%PDF-1.4\n corrupted stream without EOF")
    ctx_corrupt = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "corrupt.pdf", "local_path": str(corrupt_file)}],
        config={"text": "DRAFT"},
    )
    with pytest.raises(AppException) as exc_corrupt:
        await handler.process(ctx_corrupt)
    assert exc_corrupt.value.code == "CORRUPTED_FILE"

    # 3. Encrypted file
    enc_writer = pypdf.PdfWriter()
    p = pypdf.PageObject.create_blank_page(width=300, height=300)
    enc_writer.add_page(p)
    enc_writer.encrypt("mypassword")
    enc_bytes = io.BytesIO()
    enc_writer.write(enc_bytes)

    enc_file = tmp_path / "enc.pdf"
    enc_file.write_bytes(enc_bytes.getvalue())

    ctx_enc = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "enc.pdf", "local_path": str(enc_file)}],
        config={"text": "DRAFT"},
    )
    with pytest.raises(AppException) as exc_enc:
        await handler.process(ctx_enc)
    assert exc_enc.value.code == "DOCUMENT_ENCRYPTED"


@pytest.mark.asyncio
async def test_watermark_page_out_of_bounds(tmp_path):
    handler = WatermarkPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=2)
    in_file = tmp_path / "sample_2p.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample_2p.pdf", "local_path": str(in_file)}],
        config={"text": "DRAFT", "pages": "1-5"},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "PAGE_NUMBER_OUT_OF_BOUNDS"

