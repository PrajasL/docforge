import io
import os
import shutil
import tempfile
import uuid
import pypdf
from PIL import Image

EICAR_SIGNATURE = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)

class E2EFixturesManager:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_artifacts")
        else:
            self.base_dir = base_dir
        self.run_id = uuid.uuid4().hex[:8]
        self.fixtures_dir = os.path.join(self.base_dir, f"fixtures_{self.run_id}")
        self.download_dir = os.path.join(self.base_dir, f"downloads_{self.run_id}")
        os.makedirs(self.fixtures_dir, exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)

        self.created_files = []
        self._generate_fixtures()

    def _generate_fixtures(self):
        # 1. 1-page sample PDF
        self.pdf_1page = os.path.join(self.fixtures_dir, "sample_1page.pdf")
        self._write_sample_pdf(self.pdf_1page, pages=1, text="DocForge Test Page 1")

        # 2. 2-page sample PDF
        self.pdf_2page = os.path.join(self.fixtures_dir, "sample_2page.pdf")
        self._write_sample_pdf(self.pdf_2page, pages=2, text="DocForge Merge Document 2")

        # 3. 3-page sample PDF
        self.pdf_3page = os.path.join(self.fixtures_dir, "sample_3page.pdf")
        self._write_sample_pdf(self.pdf_3page, pages=3, text="DocForge Multi-page Document")

        # 4. Encrypted PDF with password "secret123"
        self.pdf_encrypted = os.path.join(self.fixtures_dir, "sample_encrypted.pdf")
        self._write_encrypted_pdf(self.pdf_encrypted, password="secret123")

        # 5. Corrupted PDF
        self.pdf_corrupted = os.path.join(self.fixtures_dir, "corrupt.pdf")
        with open(self.pdf_corrupted, "wb") as f:
            f.write(b"%PDF-1.4\n%Invalid Corrupted Content That Cannot Be Parsed\n%%EOF")

        # 6. Non-PDF text file
        self.txt_file = os.path.join(self.fixtures_dir, "not_a_pdf.txt")
        with open(self.txt_file, "w", encoding="utf-8") as f:
            f.write("This is a plain text file, not a valid PDF document.")

        # 7. Sample JPEG images for jpg-to-pdf
        self.jpg_1 = os.path.join(self.fixtures_dir, "image_1.jpg")
        self.jpg_2 = os.path.join(self.fixtures_dir, "image_2.jpg")
        self._write_sample_jpg(self.jpg_1, (300, 300), (220, 50, 50))
        self._write_sample_jpg(self.jpg_2, (400, 300), (50, 100, 220))

        # 8. EICAR virus signature test file
        self.eicar_pdf = os.path.join(self.fixtures_dir, "eicar_malware.pdf")
        with open(self.eicar_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n" + EICAR_SIGNATURE + b"\n%%EOF")

        # 9. Recoverable damaged PDF (corrupted startxref offset)
        self.pdf_damaged_xref = os.path.join(self.fixtures_dir, "damaged_xref.pdf")
        with open(self.pdf_2page, "rb") as f:
            valid_bytes = f.read()
        import re
        damaged_bytes = re.sub(rb"startxref\s+\d+", b"startxref\n999999999", valid_bytes)
        if damaged_bytes == valid_bytes:
            damaged_bytes = valid_bytes.replace(b"%%EOF", b"")
        with open(self.pdf_damaged_xref, "wb") as f:
            f.write(damaged_bytes)
        self.created_files.append(self.pdf_damaged_xref)

    def _write_sample_pdf(self, path: str, pages: int = 1, text: str = "Test"):
        writer = pypdf.PdfWriter()
        for i in range(pages):
            page = writer.add_blank_page(width=612, height=792)  # US Letter
        with open(path, "wb") as f:
            writer.write(f)
        self.created_files.append(path)

    def _write_encrypted_pdf(self, path: str, password: str = "secret123"):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt(password)
        with open(path, "wb") as f:
            writer.write(f)
        self.created_files.append(path)

    def _write_sample_jpg(self, path: str, size: tuple, color: tuple):
        img = Image.new("RGB", size, color=color)
        img.save(path, format="JPEG", quality=90)
        self.created_files.append(path)

    def cleanup(self):
        try:
            if os.path.exists(self.fixtures_dir):
                shutil.rmtree(self.fixtures_dir, ignore_errors=True)
            if os.path.exists(self.download_dir):
                shutil.rmtree(self.download_dir, ignore_errors=True)
        except Exception:
            pass
