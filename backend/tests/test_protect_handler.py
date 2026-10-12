import io
import os

import pypdf
import pytest

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.protect import ProtectPDFHandler


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
        job_id="test-job-protect",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


@pytest.mark.asyncio
async def test_protect_handler_success_aes256(tmp_path):
    handler = ProtectPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=3)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    password = "SuperSecretPassword123!"

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "sample.pdf", "local_path": str(in_file)}],
        config={
            "password": password,
            "confirm_password": password,
            "output_filename": "locked_sample.pdf",
        },
    )
    result = await handler.process(ctx)

    # 1. Verify result dictionary
    assert os.path.exists(result["local_path"])
    assert result["filename"] == "locked_sample.pdf"
    assert result["page_count"] == 3
    assert result["is_encrypted"] is True
    assert result["encryption_algorithm"] == "AES-256"
    assert "password" not in result  # Never expose password in result

    # 2. Verify encrypted file behavior
    reader = pypdf.PdfReader(result["local_path"])
    assert reader.is_encrypted is True

    # 3. Reading without password fails
    with pytest.raises(Exception):
        _ = len(reader.pages)

    # 4. Wrong password rejected
    reader_wrong = pypdf.PdfReader(result["local_path"])
    dec_wrong = reader_wrong.decrypt("WrongPassword")
    assert dec_wrong == 0

    # 5. Correct password decrypts and reveals all pages
    reader_correct = pypdf.PdfReader(result["local_path"])
    dec_correct = reader_correct.decrypt(password)
    assert dec_correct != 0
    assert len(reader_correct.pages) == 3
    for p in reader_correct.pages:
        assert float(p.mediabox.width) == 400.0
        assert float(p.mediabox.height) == 600.0


@pytest.mark.asyncio
async def test_protect_handler_validation_errors(tmp_path):
    handler = ProtectPDFHandler()
    pdf_bytes = create_dummy_pdf(num_pages=1)
    in_file = tmp_path / "sample.pdf"
    in_file.write_bytes(pdf_bytes)

    # 1. Missing / empty password
    with pytest.raises(AppException) as exc1:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"password": ""}))
    assert exc1.value.code == "INVALID_PASSWORD"

    # 2. Whitespace-only password
    with pytest.raises(AppException) as exc2:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"password": "   "}))
    assert exc2.value.code == "INVALID_PASSWORD"

    # 3. Excessively long password (> 128 characters)
    with pytest.raises(AppException) as exc3:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"password": "a" * 129}))
    assert exc3.value.code == "INVALID_PASSWORD"

    # 4. Password mismatch
    with pytest.raises(AppException) as exc4:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], {"password": "pass1", "confirm_password": "pass2"}))
    assert exc4.value.code == "PASSWORD_MISMATCH"

    # 5. Missing config
    with pytest.raises(AppException) as exc5:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(in_file)}], None))
    assert exc5.value.code == "INVALID_CONFIG"


@pytest.mark.asyncio
async def test_protect_handler_already_encrypted_file(tmp_path):
    handler = ProtectPDFHandler()
    enc_writer = pypdf.PdfWriter()
    enc_writer.add_blank_page(width=200, height=200)
    enc_writer.encrypt("existing_pass")
    enc_file = tmp_path / "already_enc.pdf"
    with open(enc_file, "wb") as f:
        enc_writer.write(f)

    with pytest.raises(AppException) as exc:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(enc_file)}], {"password": "new_pass"}))
    assert exc.value.code == "ALREADY_ENCRYPTED"
    assert "already password-protected" in exc.value.message


@pytest.mark.asyncio
async def test_protect_handler_corrupted_and_empty_files(tmp_path):
    handler = ProtectPDFHandler()

    # 1. Missing input file
    with pytest.raises(AppException) as exc1:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(tmp_path / "missing.pdf")}], {"password": "pwd"}))
    assert exc1.value.code == "FILE_NOT_FOUND"

    # 2. Empty input file (0 bytes)
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    with pytest.raises(AppException) as exc2:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(empty_file)}], {"password": "pwd"}))
    assert exc2.value.code == "EMPTY_INPUT_FILE"

    # 3. Corrupted PDF file
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"Not a valid PDF stream data")
    with pytest.raises(AppException) as exc3:
        await handler.process(make_context(str(tmp_path), [{"local_path": str(corrupt_file)}], {"password": "pwd"}))
    assert exc3.value.code == "CORRUPTED_FILE"
