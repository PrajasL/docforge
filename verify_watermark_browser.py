import os
import sys
import time
import json
import pypdf
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(
    os.path.expanduser("~"),
    ".gemini",
    "antigravity-ide",
    "brain",
    "e3048733-de8a-4a34-a02b-4052aa1f9c0e"
)
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

WORKSPACE_ROOT = os.path.abspath(os.path.dirname(__file__))
MULTIPAGE_PDF = os.path.join(WORKSPACE_ROOT, "rotate_test_multipage.pdf")
NON_PDF_FILE = os.path.join(WORKSPACE_ROOT, "rotate_non_pdf.txt")
CORRUPTED_PDF = os.path.join(WORKSPACE_ROOT, "rotate_corrupted.pdf")
ENCRYPTED_PDF = os.path.join(WORKSPACE_ROOT, "rotate_encrypted.pdf")

console_errors = []

def on_console(msg):
    if msg.type in ["error"]:
        if "Failed to load resource" not in msg.text and "favicon.ico" not in msg.text:
            console_errors.append(f"[{msg.type}] {msg.text}")
    print(f"Browser Console [{msg.type}]: {msg.text}", flush=True)

def main():
    print("=== Starting Real Browser Verification for Watermark PDF ===")
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda err: console_errors.append(f"[pageerror] {str(err)}"))

        # Step 1: Navigate to /watermark
        print("\n--- 1. Navigating to http://localhost:3000/watermark ---")
        page.goto("http://localhost:3000/watermark", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_watermark_initial.png"))
        h1_text = page.inner_text("h1")
        print(f"H1 Header: {h1_text}")
        assert "Add Text Watermark to PDF" in h1_text, f"Unexpected H1: {h1_text}"
        results["01_navigation"] = "PASSED"

        # Helper to wait for job completion
        def wait_for_completion(timeout_sec=30):
            start = time.time()
            while time.time() - start < timeout_sec:
                if page.locator("text='Watermark Applied Successfully!'").is_visible():
                    return True
                if page.locator("#global-error-banner").is_visible():
                    err_txt = page.locator("#global-error-banner").inner_text()
                    raise RuntimeError(f"Job failed with error banner: {err_txt}")
                page.wait_for_timeout(500)
            raise TimeoutError("Timed out waiting for completion")

        # Step 2: Diagonal Watermark (All Pages)
        print("\n--- 2. Testing Diagonal Watermark (All Pages) ---")
        page.set_input_files("#watermark-file-input", MULTIPAGE_PDF)
        page.wait_for_selector("#start-watermark-btn")
        page.fill("#watermark-text-input", "TOP SECRET")
        page.click("#pos-diagonal-btn")
        page.click("#start-watermark-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_watermark_diagonal_completed.png"))

        # Download result
        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_diag = os.path.join(DOWNLOAD_DIR, "watermarked_diagonal.pdf")
        download.save_as(dl_path_diag)

        # Verify with pypdf
        reader_diag = pypdf.PdfReader(dl_path_diag)
        assert len(reader_diag.pages) == 3, f"Expected 3 pages, got {len(reader_diag.pages)}"
        for i, pg in enumerate(reader_diag.pages):
            txt = pg.extract_text()
            assert "TOP SECRET" in txt, f"Page {i+1} missing watermark text 'TOP SECRET'"
        print("Verified Diagonal Watermark: 3 pages all stamped with 'TOP SECRET'")
        results["02_watermark_diagonal"] = "PASSED"

        # Step 3: Exact Center Watermark
        print("\n--- 3. Testing Exact Center Watermark ---")
        page.click("text='Watermark Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#watermark-file-input", MULTIPAGE_PDF)
        page.wait_for_selector("#pos-center-btn")
        page.click("#pos-center-btn")
        page.fill("#watermark-text-input", "DRAFT COPY")
        page.click("#start-watermark-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_watermark_center_completed.png"))

        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_center = os.path.join(DOWNLOAD_DIR, "watermarked_center.pdf")
        download.save_as(dl_path_center)

        reader_center = pypdf.PdfReader(dl_path_center)
        assert len(reader_center.pages) == 3
        for i, pg in enumerate(reader_center.pages):
            assert "DRAFT COPY" in pg.extract_text()
        print("Verified Center Watermark: 3 pages all stamped with 'DRAFT COPY'")
        results["03_watermark_center"] = "PASSED"

        # Step 4: Selective Pages (1, 3 only)
        print("\n--- 4. Testing Selective Pages (1, 3) Watermark ---")
        page.click("text='Watermark Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#watermark-file-input", MULTIPAGE_PDF)
        page.wait_for_selector("#scope-custom-btn")
        page.click("#scope-custom-btn")
        page.wait_for_selector("#custom-pages-input")
        page.fill("#custom-pages-input", "1, 3")
        page.fill("#watermark-text-input", "INTERNAL ONLY")
        page.click("#start-watermark-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_watermark_selective_completed.png"))

        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_sel = os.path.join(DOWNLOAD_DIR, "watermarked_selective.pdf")
        download.save_as(dl_path_sel)

        reader_sel = pypdf.PdfReader(dl_path_sel)
        assert len(reader_sel.pages) == 3
        assert "INTERNAL ONLY" in reader_sel.pages[0].extract_text()
        assert "INTERNAL ONLY" not in reader_sel.pages[1].extract_text()
        assert "INTERNAL ONLY" in reader_sel.pages[2].extract_text()
        print("Verified Selective Watermark: Page 1=Stamped, Page 2=Clean, Page 3=Stamped")
        results["04_watermark_selective"] = "PASSED"

        # Step 5: Non-PDF rejection
        print("\n--- 5. Testing Non-PDF File Rejection ---")
        page.click("text='Watermark Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#watermark-file-input", NON_PDF_FILE)
        page.wait_for_selector("#global-error-banner")
        err_non_pdf = page.locator("#global-error-banner").inner_text()
        print(f"Non-PDF error message: {err_non_pdf}")
        assert "Skipped non-PDF file" in err_non_pdf
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_watermark_error_non_pdf.png"))
        page.click("text='Dismiss'")
        results["05_error_non_pdf"] = "PASSED"

        # Step 6: Corrupted PDF handling
        print("\n--- 6. Testing Corrupted PDF Handling ---")
        page.set_input_files("#watermark-file-input", CORRUPTED_PDF)
        page.wait_for_selector("#start-watermark-btn")
        page.click("#start-watermark-btn")
        page.wait_for_selector("#global-error-banner", timeout=15000)
        err_corrupt = page.locator("#global-error-banner").inner_text()
        print(f"Corrupted PDF error message: {err_corrupt}")
        assert "corrupted" in err_corrupt.lower() or "not a valid pdf" in err_corrupt.lower()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_watermark_error_corrupted.png"))
        page.click("text='Dismiss'")
        results["06_error_corrupted"] = "PASSED"

        # Step 7: Encrypted PDF handling
        print("\n--- 7. Testing Encrypted PDF Handling ---")
        page.click("[title='Remove file']")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#watermark-file-input", ENCRYPTED_PDF)
        page.wait_for_selector("#start-watermark-btn")
        page.click("#start-watermark-btn")
        page.wait_for_selector("#global-error-banner", timeout=15000)
        err_enc = page.locator("#global-error-banner").inner_text()
        print(f"Encrypted PDF error message: {err_enc}")
        assert "password" in err_enc.lower() or "encrypted" in err_enc.lower()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_watermark_error_encrypted.png"))
        page.click("text='Dismiss'")
        results["07_error_encrypted"] = "PASSED"

        # Step 8: Out of bounds custom page range
        print("\n--- 8. Testing Out of Bounds Custom Page Range ---")
        page.click("[title='Remove file']")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#watermark-file-input", MULTIPAGE_PDF)
        page.wait_for_selector("#scope-custom-btn")
        page.click("#scope-custom-btn")
        page.fill("#custom-pages-input", "10-20")
        page.click("#start-watermark-btn")
        page.wait_for_selector("#global-error-banner", timeout=15000)
        err_bounds = page.locator("#global-error-banner").inner_text()
        print(f"Out of bounds error message: {err_bounds}")
        assert "exceeds total pages" in err_bounds.lower() or "out of bounds" in err_bounds.lower()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_watermark_error_bounds.png"))
        results["08_error_out_of_bounds"] = "PASSED"

        # Step 9: Regression check navigation (/merge, /split, /compress, /rotate)
        print("\n--- 9. Regression Check: /merge, /split, /compress, /rotate ---")
        page.goto("http://localhost:3000/merge", wait_until="networkidle")
        assert "Merge PDF Files" in page.inner_text("h1")

        page.goto("http://localhost:3000/split", wait_until="networkidle")
        assert "Split PDF Document" in page.inner_text("h1")

        page.goto("http://localhost:3000/compress", wait_until="networkidle")
        assert "Compress PDF Document" in page.inner_text("h1")

        page.goto("http://localhost:3000/rotate", wait_until="networkidle")
        assert "Rotate PDF Pages Permanently" in page.inner_text("h1")
        results["09_regressions"] = "PASSED"

        browser.close()

    print("\n=== SUMMARY OF BROWSER VERIFICATION RESULTS ===")
    for k, v in results.items():
        print(f"{k}: {v}")
    print(f"Console errors recorded: {len(console_errors)}")
    if console_errors:
        for err in console_errors:
            print(f"  {err}")

    assert all(v == "PASSED" for v in results.values())
    print("\nALL WATERMARK BROWSER VERIFICATION STEPS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
