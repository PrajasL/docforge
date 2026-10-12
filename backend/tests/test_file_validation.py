import pytest

from app.files.validator import (
    FileValidationError,
    sanitize_filename,
    validate_content_type,
    validate_file_extension,
    validate_pdf_file,
    validate_pdf_magic_bytes,
)


def test_sanitize_filename():
    assert sanitize_filename("simple.pdf") == "simple.pdf"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename(r"C:\Windows\System32\cmd.exe.pdf") == "cmd.exe.pdf"
    assert sanitize_filename("my document.pdf") == "my document.pdf"
    assert sanitize_filename("unsafe#$*()name.pdf") == "unsafe_____name.pdf"
    # Adds extension if missing
    assert sanitize_filename("no_ext") == "no_ext.pdf"
    # Handles None or empty
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename(None) == "document.pdf"


def test_validate_file_extension():
    assert validate_file_extension("document.pdf") is True
    assert validate_file_extension("DOCUMENT.PDF") is True
    assert validate_file_extension("document.doc") is False
    assert validate_file_extension("document.exe") is False
    assert validate_file_extension("") is False


def test_validate_content_type():
    assert validate_content_type("application/pdf") is True
    assert validate_content_type("application/x-pdf") is True
    assert validate_content_type("APPLICATION/PDF") is True
    assert validate_content_type("text/plain") is False
    assert validate_content_type("image/png") is False
    assert validate_content_type("") is False


def test_validate_pdf_magic_bytes():
    valid_pdf_start = b"%PDF-1.7\nsome binary content..."
    assert validate_pdf_magic_bytes(valid_pdf_start) is True

    # PDF with leading comment / whitespace (spec allows up to 1024 bytes)
    valid_pdf_offset = b"\xef\xbb\xbf%PDF-2.0\n..."
    assert validate_pdf_magic_bytes(valid_pdf_offset) is True

    # Non-PDF content
    assert validate_pdf_magic_bytes(b"\x89PNG\r\n\x1a\n") is False
    assert validate_pdf_magic_bytes(b"PK\x03\x04") is False
    assert validate_pdf_magic_bytes(b"Hello world, I am a text file") is False
    assert validate_pdf_magic_bytes(b"") is False


def test_validate_pdf_file_success():
    valid_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    validate_pdf_file(
        content=valid_data,
        filename="valid.pdf",
        content_type="application/pdf",
        max_size_bytes=1024 * 1024,
    )


def test_validate_pdf_file_failures():
    # Empty file
    with pytest.raises(FileValidationError) as exc:
        validate_pdf_file(content=b"", filename="empty.pdf")
    assert exc.value.code == "VALIDATION_ERROR"

    # Oversized file
    big_data = b"%PDF-" + b"0" * 200
    with pytest.raises(FileValidationError) as exc:
        validate_pdf_file(content=big_data, max_size_bytes=100)
    assert exc.value.code == "FILE_TOO_LARGE"

    # Wrong extension
    with pytest.raises(FileValidationError) as exc:
        validate_pdf_file(content=b"%PDF-1.4", filename="document.docx")
    assert exc.value.code == "INVALID_CONTENT_TYPE"

    # Wrong content type
    with pytest.raises(FileValidationError) as exc:
        validate_pdf_file(content=b"%PDF-1.4", content_type="image/jpeg")
    assert exc.value.code == "INVALID_CONTENT_TYPE"

    # Fake extension but invalid magic bytes
    fake_pdf = b"This is just a text file renamed to .pdf"
    with pytest.raises(FileValidationError) as exc:
        validate_pdf_file(content=fake_pdf, filename="fake.pdf")
    assert exc.value.code == "INVALID_CONTENT_TYPE"
