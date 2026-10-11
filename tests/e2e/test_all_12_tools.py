import os
import sys
import time
import io
import zipfile
import pypdf
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from playwright.sync_api import sync_playwright
from tests.e2e.fixtures_manager import E2EFixturesManager

BASE_URL = "http://localhost:3000"

def wait_for_job_completion(page, download_selector, timeout=35):
    start = time.time()
    while time.time() - start < timeout:
        if page.locator(download_selector).is_visible():
            return True
        if page.locator("#global-error-banner").is_visible() and "hidden" not in (page.locator("#global-error-banner").get_attribute("class") or ""):
            err = page.locator("#global-error-banner").inner_text()
            raise RuntimeError(f"Job failed with error banner: {err}")
        alert = page.locator("[role='alert']")
        if alert.is_visible() and alert.inner_text().strip():
            raise RuntimeError(f"Job failed with alert: {alert.inner_text().strip()}")
        page.wait_for_timeout(500)
    raise TimeoutError(f"Timed out waiting for completion selector: {download_selector}")

def download_file(page, button_selector, target_path, timeout=15000):
    with page.expect_download(timeout=timeout) as download_info:
        page.locator(button_selector).click()
    download = download_info.value
    download.save_as(target_path)
    assert os.path.exists(target_path), f"Downloaded file not found at {target_path}"
    assert os.path.getsize(target_path) > 0, "Downloaded file is empty"
    return target_path

def run_all_12_tools_tests():
    fixtures = E2EFixturesManager()
    results = {}
    print("=== Starting E2E Tests for All 12 Tools ===")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # 1. Merge PDF
            print("\n[1/12] Testing /merge...")
            page.goto(f"{BASE_URL}/merge", wait_until="networkidle")
            page.locator("#merge-file-input").set_input_files([fixtures.pdf_1page, fixtures.pdf_2page])
            page.wait_for_selector("[data-testid='file-item-0']", timeout=5000)
            page.locator("#merge-action-btn").click()
            wait_for_job_completion(page, "#download-merged-pdf-btn")
            out_merge = os.path.join(fixtures.download_dir, "merged.pdf")
            download_file(page, "#download-merged-pdf-btn", out_merge)
            reader = pypdf.PdfReader(out_merge)
            assert len(reader.pages) == 3, f"Expected 3 pages, got {len(reader.pages)}"
            results["merge"] = "PASSED (3 pages verified)"
            print(f" -> {results['merge']}")

            # 2. Split PDF
            print("\n[2/12] Testing /split...")
            page.goto(f"{BASE_URL}/split", wait_until="networkidle")
            page.locator("#split-file-input").set_input_files(fixtures.pdf_3page)
            page.wait_for_selector("#page-ranges-input", timeout=5000)
            page.locator("#page-ranges-input").fill("1-2, 3")
            page.locator("#split-action-btn").click()
            wait_for_job_completion(page, "#download-split-zip-btn")
            out_split = os.path.join(fixtures.download_dir, "split.zip")
            download_file(page, "#download-split-zip-btn", out_split)
            with zipfile.ZipFile(out_split, "r") as z:
                names = z.namelist()
                assert len(names) >= 1, "Split zip is empty"
            results["split"] = f"PASSED ({len(names)} items in zip)"
            print(f" -> {results['split']}")

            # 3. Compress PDF
            print("\n[3/12] Testing /compress...")
            page.goto(f"{BASE_URL}/compress", wait_until="networkidle")
            page.locator("#compress-file-input").set_input_files(fixtures.pdf_3page)
            page.wait_for_selector("#compress-action-btn", timeout=5000)
            page.locator("#compress-action-btn").click()
            wait_for_job_completion(page, "#download-compressed-pdf-btn")
            out_compress = os.path.join(fixtures.download_dir, "compressed.pdf")
            download_file(page, "#download-compressed-pdf-btn", out_compress)
            reader = pypdf.PdfReader(out_compress)
            assert len(reader.pages) == 3
            results["compress"] = "PASSED (Valid compressed PDF, 3 pages)"
            print(f" -> {results['compress']}")

            # 4. Rotate PDF
            print("\n[4/12] Testing /rotate...")
            page.goto(f"{BASE_URL}/rotate", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_3page)
            page.wait_for_selector("#angle-90-btn", timeout=5000)
            page.locator("#angle-90-btn").click()
            page.locator("#start-rotate-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_rotate = os.path.join(fixtures.download_dir, "rotated.pdf")
            download_file(page, "#download-result-btn", out_rotate)
            reader = pypdf.PdfReader(out_rotate)
            assert len(reader.pages) == 3
            assert reader.pages[0].rotation == 90, f"Expected rotation 90, got {reader.pages[0].rotation}"
            results["rotate"] = "PASSED (90 deg rotation verified)"
            print(f" -> {results['rotate']}")

            # 5. Watermark PDF
            print("\n[5/12] Testing /watermark...")
            page.goto(f"{BASE_URL}/watermark", wait_until="networkidle")
            page.locator("#watermark-file-input").set_input_files(fixtures.pdf_1page)
            page.wait_for_selector("#watermark-text-input", timeout=5000)
            page.locator("#watermark-text-input").fill("CONFIDENTIAL")
            page.locator("#start-watermark-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_watermark = os.path.join(fixtures.download_dir, "watermarked.pdf")
            download_file(page, "#download-result-btn", out_watermark)
            reader = pypdf.PdfReader(out_watermark)
            assert len(reader.pages) == 1
            results["watermark"] = "PASSED (Watermarked PDF verified)"
            print(f" -> {results['watermark']}")

            # 6. Page Numbers
            print("\n[6/12] Testing /page-numbers...")
            page.goto(f"{BASE_URL}/page-numbers", wait_until="networkidle")
            page.locator("#page-numbers-file-input").set_input_files(fixtures.pdf_3page)
            page.wait_for_selector("#start-page-numbers-btn", timeout=5000)
            page.locator("#start-page-numbers-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_pn = os.path.join(fixtures.download_dir, "numbered.pdf")
            download_file(page, "#download-result-btn", out_pn)
            reader = pypdf.PdfReader(out_pn)
            assert len(reader.pages) == 3
            results["page-numbers"] = "PASSED (Numbered PDF verified, 3 pages)"
            print(f" -> {results['page-numbers']}")

            # 7. Protect PDF
            print("\n[7/12] Testing /protect...")
            page.goto(f"{BASE_URL}/protect", wait_until="networkidle")
            page.locator("#protect-file-input").set_input_files(fixtures.pdf_1page)
            page.wait_for_selector("#password-input", timeout=5000)
            page.locator("#password-input").fill("DocForgePass123")
            page.locator("#confirm-password-input").fill("DocForgePass123")
            page.locator("#start-protect-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_protect = os.path.join(fixtures.download_dir, "protected.pdf")
            download_file(page, "#download-result-btn", out_protect)
            reader = pypdf.PdfReader(out_protect)
            assert reader.is_encrypted, "Output PDF is not encrypted"
            assert reader.decrypt("DocForgePass123") > 0, "Decryption failed with password"
            results["protect"] = "PASSED (Encrypted & decrypted with password)"
            print(f" -> {results['protect']}")

            # 8. Unlock PDF
            print("\n[8/12] Testing /unlock...")
            page.goto(f"{BASE_URL}/unlock", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_encrypted)
            page.wait_for_selector("#password-input", timeout=5000)
            page.locator("#password-input").fill("secret123")
            page.locator("#unlock-submit-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_unlock = os.path.join(fixtures.download_dir, "unlocked.pdf")
            download_file(page, "#download-result-btn", out_unlock)
            reader = pypdf.PdfReader(out_unlock)
            assert not reader.is_encrypted, "Output PDF should not be encrypted"
            results["unlock"] = "PASSED (Unlocked PDF is decrypted)"
            print(f" -> {results['unlock']}")

            # 9. Extract Pages
            print("\n[9/12] Testing /extract-pages...")
            page.goto(f"{BASE_URL}/extract-pages", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_3page)
            page.wait_for_selector("#page-ranges-input", timeout=5000)
            page.locator("#page-ranges-input").fill("1-2")
            page.locator("#extract-submit-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_extract = os.path.join(fixtures.download_dir, "extracted.pdf")
            download_file(page, "#download-result-btn", out_extract)
            reader = pypdf.PdfReader(out_extract)
            assert len(reader.pages) == 2, f"Expected 2 extracted pages, got {len(reader.pages)}"
            results["extract-pages"] = "PASSED (2 pages extracted)"
            print(f" -> {results['extract-pages']}")

            # 10. Organize PDF
            print("\n[10/12] Testing /organize-pdf...")
            page.goto(f"{BASE_URL}/organize-pdf", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_3page)
            page.wait_for_selector("#organize-submit-btn", timeout=5000)
            page.locator("#organize-submit-btn").click()
            wait_for_job_completion(page, "#download-btn")
            out_organize = os.path.join(fixtures.download_dir, "organized.pdf")
            download_file(page, "#download-btn", out_organize)
            reader = pypdf.PdfReader(out_organize)
            assert len(reader.pages) == 3
            results["organize-pdf"] = "PASSED (Organized PDF verified, 3 pages)"
            print(f" -> {results['organize-pdf']}")

            # 11. PDF to JPG
            print("\n[11/12] Testing /pdf-to-jpg...")
            page.goto(f"{BASE_URL}/pdf-to-jpg", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_1page)
            page.wait_for_selector("#pdf-to-jpg-submit-btn", timeout=5000)
            page.locator("#pdf-to-jpg-submit-btn").click()
            wait_for_job_completion(page, "#download-result-btn")
            out_jpg_zip = os.path.join(fixtures.download_dir, "pages_jpg.zip")
            download_file(page, "#download-result-btn", out_jpg_zip)
            with zipfile.ZipFile(out_jpg_zip, "r") as z:
                names = [n for n in z.namelist() if n.lower().endswith(".jpg") or n.lower().endswith(".jpeg")]
                assert len(names) >= 1, "No JPG images in zip"
                # verify image data
                img_data = z.read(names[0])
                img = Image.open(io.BytesIO(img_data))
                assert img.format == "JPEG"
            results["pdf-to-jpg"] = f"PASSED (ZIP with {len(names)} valid JPEG images)"
            print(f" -> {results['pdf-to-jpg']}")

            # 12. JPG to PDF
            print("\n[12/13] Testing /jpg-to-pdf...")
            page.goto(f"{BASE_URL}/jpg-to-pdf", wait_until="networkidle")
            file_input = page.locator("input[type='file']")
            file_input.set_input_files([fixtures.jpg_1, fixtures.jpg_2])
            convert_btn = page.locator("button:has-text('Convert to PDF')")
            convert_btn.wait_for(timeout=5000)
            convert_btn.click()
            download_btn = page.locator("button:has-text('Download PDF')")
            start_wait = time.time()
            while time.time() - start_wait < 35:
                if download_btn.is_visible():
                    break
                page.wait_for_timeout(500)
            assert download_btn.is_visible(), "Download PDF button not visible"
            out_jpg_pdf = os.path.join(fixtures.download_dir, "converted.pdf")
            download_file(page, "button:has-text('Download PDF')", out_jpg_pdf)
            reader = pypdf.PdfReader(out_jpg_pdf)
            assert len(reader.pages) == 2, f"Expected 2 pages in PDF, got {len(reader.pages)}"
            results["jpg-to-pdf"] = "PASSED (2 JPGs converted to 2-page PDF)"
            print(f" -> {results['jpg-to-pdf']}")

            # 13. Repair PDF
            print("\n[13/13] Testing /repair-pdf...")
            page.goto(f"{BASE_URL}/repair-pdf", wait_until="networkidle")
            page.locator("#repair-file-input").set_input_files(fixtures.pdf_damaged_xref)
            page.wait_for_selector("#repair-action-btn", timeout=5000)
            page.locator("#repair-action-btn").click()
            wait_for_job_completion(page, "#download-repaired-pdf-btn")
            out_repaired = os.path.join(fixtures.download_dir, "repaired.pdf")
            download_file(page, "#download-repaired-pdf-btn", out_repaired)
            reader = pypdf.PdfReader(out_repaired)
            assert len(reader.pages) == 2, f"Expected 2 pages in repaired PDF, got {len(reader.pages)}"
            results["repair-pdf"] = "PASSED (Recovered damaged xref PDF to 2 valid pages)"
            print(f" -> {results['repair-pdf']}")

            browser.close()
    finally:
        fixtures.cleanup()

    print("\n=== SUMMARY OF ALL 13 TOOLS ===")
    for tool, res in results.items():
        print(f"  [{tool.upper()}]: {res}")
    assert len(results) == 13, f"Expected 13 tools tested, got {len(results)}"
    return results

if __name__ == "__main__":
    import io
    run_all_12_tools_tests()

