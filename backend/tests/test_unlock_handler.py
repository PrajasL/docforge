import io
import os

import pypdf
import pytest

from app.core.errors import AppException
from app.tools.base import ProcessingContext
from app.tools.unlock import UnlockPDFHandler


def create_encrypted_pdf(password: str = "Secret123!", num_pages: int = 3, width: float = 400, height: float = 600) -> bytes:
    """Creates a password-protected PDF using AES-256."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        page = pypdf.PageObject.create_blank_page(width=width, height=height)
        writer.add_page(page)
    writer.add_metadata({"/Title": "Confidential Report", "/Author": "DocForge Team"})
    writer.encrypt(user_password=password, algorithm="AES-256")
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def create_unencrypted_pdf(num_pages: int = 2) -> bytes:
    """Creates a regular, unencrypted PDF."""
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=300, height=400)
    bio = io.BytesIO()
    writer.write(bio)
    return bio.getvalue()


def make_context(temp_dir: str, input_files: list, config: dict = None) -> ProcessingContext:
    async def dummy_progress(p: int):
        pass

    return ProcessingContext(
        job_id="test-job-unlock",
        input_files=input_files,
        config=config or {},
        temp_dir=temp_dir,
        progress_callback=dummy_progress,
    )


@pytest.mark.asyncio
async def test_unlock_handler_success(tmp_path):
    handler = UnlockPDFHandler()
    password = "MySecurePassword_2026!"
    pdf_bytes = create_encrypted_pdf(password=password, num_pages=3)
    in_file = tmp_path / "protected_sample.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "protected_sample.pdf", "local_path": str(in_file)}],
        config={
            "password": password,
            "output_filename": "decrypted_sample.pdf",
        },
    )
    result = await handler.process(ctx)

    # 1. Verify result dictionary
    assert os.path.exists(result["local_path"])
    assert result["filename"] == "decrypted_sample.pdf"
    assert result["page_count"] == 3
    assert result["is_encrypted"] is False
    assert "password" not in result  # Sensitive password never exposed in return dict

    # 2. Verify output file opens cleanly without ANY password
    reader = pypdf.PdfReader(result["local_path"])
    assert reader.is_encrypted is False
    assert len(reader.pages) == 3
    for p in reader.pages:
        assert float(p.mediabox.width) == 400.0
        assert float(p.mediabox.height) == 600.0


@pytest.mark.asyncio
async def test_unlock_handler_default_filename(tmp_path):
    handler = UnlockPDFHandler()
    password = "TestPassword99"
    pdf_bytes = create_encrypted_pdf(password=password, num_pages=1)
    in_file = tmp_path / "protected_document.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "protected_document.pdf", "local_path": str(in_file)}],
        config={"password": password},
    )
    result = await handler.process(ctx)
    assert result["filename"] == "unlocked_document.pdf"
    assert result["is_encrypted"] is False


@pytest.mark.asyncio
async def test_unlock_handler_incorrect_password(tmp_path):
    handler = UnlockPDFHandler()
    password = "RealPassword123"
    pdf_bytes = create_encrypted_pdf(password=password, num_pages=2)
    in_file = tmp_path / "protected.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "protected.pdf", "local_path": str(in_file)}],
        config={"password": "WrongPasswordAttempt"},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "INCORRECT_PASSWORD"
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_unlock_handler_not_encrypted(tmp_path):
    handler = UnlockPDFHandler()
    pdf_bytes = create_unencrypted_pdf(num_pages=2)
    in_file = tmp_path / "plain.pdf"
    in_file.write_bytes(pdf_bytes)

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "plain.pdf", "local_path": str(in_file)}],
        config={"password": "AnyPassword"},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "NOT_ENCRYPTED"
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_unlock_handler_empty_password_validation(tmp_path):
    handler = UnlockPDFHandler()
    pdf_bytes = create_encrypted_pdf(password="SomePassword")
    in_file = tmp_path / "protected.pdf"
    in_file.write_bytes(pdf_bytes)

    # Empty string
    with pytest.raises(AppException) as exc1:
        await handler.process(
            make_context(str(tmp_path), [{"original_name": "protected.pdf", "local_path": str(in_file)}], {"password": ""})
        )
    assert exc1.value.code == "INVALID_PASSWORD"

    # Whitespace only
    with pytest.raises(AppException) as exc2:
        await handler.process(
            make_context(str(tmp_path), [{"original_name": "protected.pdf", "local_path": str(in_file)}], {"password": "   "})
        )
    assert exc2.value.code == "INVALID_PASSWORD"


@pytest.mark.asyncio
async def test_unlock_handler_corrupted_file(tmp_path):
    handler = UnlockPDFHandler()
    bad_file = tmp_path / "broken.pdf"
    bad_file.write_bytes(b"%PDF-1.4\nCorrupted binary garbage header footer missing")

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "broken.pdf", "local_path": str(bad_file)}],
        config={"password": "password"},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "CORRUPTED_FILE"


@pytest.mark.asyncio
async def test_unlock_handler_empty_file(tmp_path):
    handler = UnlockPDFHandler()
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")

    ctx = make_context(
        temp_dir=str(tmp_path),
        input_files=[{"original_name": "empty.pdf", "local_path": str(empty_file)}],
        config={"password": "password"},
    )
    with pytest.raises(AppException) as exc:
        await handler.process(ctx)
    assert exc.value.code == "EMPTY_INPUT_FILE"
