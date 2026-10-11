import io
import os
import shutil
import tempfile
import pytest
import pypdf
import pikepdf

from app.core.errors import AppException
from app.tools.repair import RepairPDFHandler
from app.tools.base import ProcessingContext


def create_sample_pdf(num_pages: int = 2, width: float = 200, height: float = 300) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=width, height=height)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_encrypted_pdf(password: str = "secret") -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def temp_workspace():
    dirpath = tempfile.mkdtemp(prefix="docforge_test_repair_")
    yield dirpath
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.mark.asyncio
async def test_repair_valid_undamaged_pdf(temp_workspace):
    handler = RepairPDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=3)
    input_path = os.path.join(temp_workspace, "sound.pdf")
    with open(input_path, "wb") as f:
        f.write(pdf_bytes)

    progresses = []

    async def on_progress(p: int):
        progresses.append(p)

    context = ProcessingContext(
        job_id="test_job_1",
        input_files=[{"id": "f1", "original_name": "sound.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=on_progress,
    )

    res = await handler.process(context)
    assert res["repaired"] is False
    assert res["repair_action"] == "VERIFIED_SOUND"
    assert res["page_count"] == 3
    assert os.path.exists(res["output_path"])
    assert res["filename"] == "repaired_sound.pdf"
    assert len(progresses) >= 3

    # Verify output is a valid readable PDF
    reader = pypdf.PdfReader(res["output_path"])
    assert len(reader.pages) == 3


@pytest.mark.asyncio
async def test_repair_damaged_startxref_offset(temp_workspace):
    handler = RepairPDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=2)

    # Inject corrupt startxref offset
    idx = pdf_bytes.rfind(b"startxref\n")
    assert idx != -1
    line_end = pdf_bytes.find(b"\n", idx + 10)
    damaged_bytes = pdf_bytes[:idx + 10] + b"9999999\n" + pdf_bytes[line_end + 1:]

    input_path = os.path.join(temp_workspace, "damaged_startxref.pdf")
    with open(input_path, "wb") as f:
        f.write(damaged_bytes)

    context = ProcessingContext(
        job_id="test_job_2",
        input_files=[{"id": "f2", "original_name": "damaged_startxref.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    res = await handler.process(context)
    assert res["repaired"] is True
    assert res["repair_action"] == "XREF_RECONSTRUCTED"
    assert res["page_count"] == 2
    assert os.path.exists(res["output_path"])

    # Verify repaired output opens without errors in pikepdf and pypdf
    with pikepdf.Pdf.open(res["output_path"], attempt_recovery=False) as verified:
        assert len(verified.pages) == 2


@pytest.mark.asyncio
async def test_repair_corrupted_xref_keyword(temp_workspace):
    handler = RepairPDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=1)
    damaged_bytes = pdf_bytes.replace(b"xref\n", b"xxxx\n")

    input_path = os.path.join(temp_workspace, "damaged_xref.pdf")
    with open(input_path, "wb") as f:
        f.write(damaged_bytes)

    context = ProcessingContext(
        job_id="test_job_3",
        input_files=[{"id": "f3", "original_name": "damaged_xref.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    res = await handler.process(context)
    assert res["repaired"] is True
    assert res["page_count"] == 1
    assert os.path.exists(res["output_path"])


@pytest.mark.asyncio
async def test_repair_missing_eof_marker(temp_workspace):
    handler = RepairPDFHandler()
    pdf_bytes = create_sample_pdf(num_pages=2)
    damaged_bytes = pdf_bytes.replace(b"%%EOF", b"")

    input_path = os.path.join(temp_workspace, "damaged_eof.pdf")
    with open(input_path, "wb") as f:
        f.write(damaged_bytes)

    context = ProcessingContext(
        job_id="test_job_4",
        input_files=[{"id": "f4", "original_name": "damaged_eof.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    res = await handler.process(context)
    assert res["page_count"] == 2
    assert os.path.exists(res["output_path"])


@pytest.mark.asyncio
async def test_repair_encrypted_pdf_rejected(temp_workspace):
    handler = RepairPDFHandler()
    encrypted_bytes = create_encrypted_pdf("secretpass")

    input_path = os.path.join(temp_workspace, "encrypted.pdf")
    with open(input_path, "wb") as f:
        f.write(encrypted_bytes)

    context = ProcessingContext(
        job_id="test_job_enc",
        input_files=[{"id": "fenc", "original_name": "encrypted.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(context)
    assert exc_info.value.code == "PDF_ENCRYPTED"
    assert "password-protected" in exc_info.value.message


@pytest.mark.asyncio
async def test_repair_empty_file_rejected(temp_workspace):
    handler = RepairPDFHandler()
    input_path = os.path.join(temp_workspace, "empty.pdf")
    with open(input_path, "wb") as f:
        pass

    context = ProcessingContext(
        job_id="test_job_empty",
        input_files=[{"id": "fe", "original_name": "empty.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(context)
    assert exc_info.value.code == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_repair_unrecoverable_garbage_rejected(temp_workspace):
    handler = RepairPDFHandler()
    garbage_bytes = b"%PDF-1.4\n" + b"\x00\xff\xee\xdd" * 50 + b"\n%%EOF"

    input_path = os.path.join(temp_workspace, "garbage.pdf")
    with open(input_path, "wb") as f:
        f.write(garbage_bytes)

    context = ProcessingContext(
        job_id="test_job_garb",
        input_files=[{"id": "fg", "original_name": "garbage.pdf", "local_path": input_path}],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    with pytest.raises(AppException) as exc_info:
        await handler.process(context)
    assert exc_info.value.code in ["UNRECOVERABLE_PDF", "EMPTY_DOCUMENT"]


@pytest.mark.asyncio
async def test_repair_custom_output_filename(temp_workspace):
    handler = RepairPDFHandler()
    handler.validate_config({"output_filename": "restored_doc.pdf"})

    pdf_bytes = create_sample_pdf(num_pages=1)
    input_path = os.path.join(temp_workspace, "input.pdf")
    with open(input_path, "wb") as f:
        f.write(pdf_bytes)

    context = ProcessingContext(
        job_id="test_job_cust",
        input_files=[{"id": "fc", "original_name": "input.pdf", "local_path": input_path}],
        config={"output_filename": "restored_doc.pdf"},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )

    res = await handler.process(context)
    assert res["filename"] == "restored_doc.pdf"


@pytest.mark.asyncio
async def test_repair_invalid_file_count(temp_workspace):
    handler = RepairPDFHandler()
    context = ProcessingContext(
        job_id="test_job_invalid_count",
        input_files=[],
        config={},
        temp_dir=temp_workspace,
        progress_callback=lambda p: None,
    )
    with pytest.raises(AppException) as exc_info:
        await handler.process(context)
    assert exc_info.value.code == "INVALID_FILE_COUNT"
