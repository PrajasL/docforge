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
    # Filter expected 400/404 fetch responses during error testing
    if msg.type in ["error"]:
        if "Failed to load resource" not in msg.text and "favicon.ico" not in msg.text:
            console_errors.append(f"[{msg.type}] {msg.text}")
    print(f"Browser Console [{msg.type}]: {msg.text}", flush=True)

def main():
    print("=== Starting Real Browser Verification for Rotate PDF ===")
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda err: console_errors.append(f"[pageerror] {str(err)}"))

        # Step 1: Navigate to /rotate
        print("\n--- 1. Navigating to http://localhost:3000/rotate ---")
        page.goto("http://localhost:3000/rotate", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_rotate_initial.png"))
        h1_text = page.inner_text("h1")
        print(f"H1 Header: {h1_text}")
        assert "Rotate PDF Pages Permanently" in h1_text, f"Unexpected H1: {h1_text}"
        results["01_navigation"] = "PASSED"

        # Helper to wait for job completion
        def wait_for_completion(timeout_sec=30):
            start = time.time()
            while time.time() - start < timeout_sec:
                if page.locator("text='Rotation Complete!'").is_visible():
                    return True
                if page.locator("#global-error-banner").is_visible():
                    err_txt = page.locator("#global-error-banner").inner_text()
                    raise RuntimeError(f"Job failed with error banner: {err_txt}")
                page.wait_for_timeout(500)
            raise TimeoutError("Timed out waiting for completion")

        # Step 2: Test 90 deg rotation (All pages)
        print("\n--- 2. Testing 90° Clockwise Rotation (All Pages) ---")
        page.set_input_files("#pdf-upload-input", MULTIPAGE_PDF)
        page.wait_for_selector("#start-rotate-btn")
        page.click("#start-rotate-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_rotate_90_completed.png"))
        
        # Download result
        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_90 = os.path.join(DOWNLOAD_DIR, "rotated_90.pdf")
        download.save_as(dl_path_90)
        
        # Verify with pypdf
        reader_90 = pypdf.PdfReader(dl_path_90)
        assert len(reader_90.pages) == 3, f"Expected 3 pages, got {len(reader_90.pages)}"
        for i, pg in enumerate(reader_90.pages):
            rot = pg.get("/Rotate", 0)
            assert rot == 90, f"Page {i+1} rotation expected 90, got {rot}"
        print(f"Verified 90° output: 3 pages all rotated to 90°")
        results["02_rotate_90"] = "PASSED"

        # Step 3: Test 180 deg rotation (All pages)
        print("\n--- 3. Testing 180° Flip Rotation (All Pages) ---")
        page.click("text='Rotate Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#pdf-upload-input", MULTIPAGE_PDF)
        page.wait_for_selector("#angle-180-btn")
        page.click("#angle-180-btn")
        page.click("#start-rotate-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_rotate_180_completed.png"))

        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_180 = os.path.join(DOWNLOAD_DIR, "rotated_180.pdf")
        download.save_as(dl_path_180)

        reader_180 = pypdf.PdfReader(dl_path_180)
        assert len(reader_180.pages) == 3
        for i, pg in enumerate(reader_180.pages):
            rot = pg.get("/Rotate", 0)
            assert rot == 180, f"Page {i+1} rotation expected 180, got {rot}"
        print(f"Verified 180° output: 3 pages all rotated to 180°")
        results["03_rotate_180"] = "PASSED"

        # Step 4: Test 270 deg rotation (All pages)
        print("\n--- 4. Testing 270° Left Rotation (All Pages) ---")
        page.click("text='Rotate Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#pdf-upload-input", MULTIPAGE_PDF)
        page.wait_for_selector("#angle-270-btn")
        page.click("#angle-270-btn")
        page.click("#start-rotate-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_rotate_270_completed.png"))

        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_270 = os.path.join(DOWNLOAD_DIR, "rotated_270.pdf")
        download.save_as(dl_path_270)

        reader_270 = pypdf.PdfReader(dl_path_270)
        assert len(reader_270.pages) == 3
        for i, pg in enumerate(reader_270.pages):
            rot = pg.get("/Rotate", 0)
            assert rot == 270, f"Page {i+1} rotation expected 270, got {rot}"
        print(f"Verified 270° output: 3 pages all rotated to 270°")
        results["04_rotate_270"] = "PASSED"

        # Step 5: Test Selective Pages rotation (pages 1 and 3 only)
        print("\n--- 5. Testing Selective Pages (1, 3) 90° Rotation ---")
        page.click("text='Rotate Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#pdf-upload-input", MULTIPAGE_PDF)
        page.wait_for_selector("#scope-custom-btn")
        page.click("#scope-custom-btn")
        page.wait_for_selector("#custom-pages-input")
        page.fill("#custom-pages-input", "1, 3")
        page.click("#angle-90-btn")
        page.click("#start-rotate-btn")
        wait_for_completion()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_rotate_selective_completed.png"))

        with page.expect_download() as download_info:
            page.click("#download-result-btn")
        download = download_info.value
        dl_path_sel = os.path.join(DOWNLOAD_DIR, "rotated_selective.pdf")
        download.save_as(dl_path_sel)

        reader_sel = pypdf.PdfReader(dl_path_sel)
        assert len(reader_sel.pages) == 3
        p1_rot = reader_sel.pages[0].get("/Rotate", 0)
        p2_rot = reader_sel.pages[1].get("/Rotate", 0)
        p3_rot = reader_sel.pages[2].get("/Rotate", 0)
        assert p1_rot == 90, f"Page 1 rotation expected 90, got {p1_rot}"
        assert p2_rot == 0, f"Page 2 rotation expected 0, got {p2_rot}"
        assert p3_rot == 90, f"Page 3 rotation expected 90, got {p3_rot}"
        print(f"Verified selective rotation: Page 1=90°, Page 2=0°, Page 3=90°")
        results["05_rotate_selective"] = "PASSED"

        # Step 6: Non-PDF rejection
        print("\n--- 6. Testing Non-PDF File Rejection ---")
        page.click("text='Rotate Another PDF'")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#pdf-upload-input", NON_PDF_FILE)
        page.wait_for_selector("#global-error-banner")
        err_non_pdf = page.locator("#global-error-banner").inner_text()
        print(f"Non-PDF error message: {err_non_pdf}")
        assert "Skipped non-PDF file" in err_non_pdf
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_error_non_pdf.png"))
        page.click("text='Dismiss'")
        results["06_error_non_pdf"] = "PASSED"

        # Step 7: Corrupted PDF handling
        print("\n--- 7. Testing Corrupted PDF Handling ---")
        page.set_input_files("#pdf-upload-input", CORRUPTED_PDF)
        page.wait_for_selector("#start-rotate-btn")
        page.click("#start-rotate-btn")
        page.wait_for_selector("#global-error-banner", timeout=15000)
        err_corrupt = page.locator("#global-error-banner").inner_text()
        print(f"Corrupted PDF error message: {err_corrupt}")
        assert "corrupted" in err_corrupt.lower() or "not a valid pdf" in err_corrupt.lower()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_error_corrupted.png"))
        page.click("text='Dismiss'")
        results["07_error_corrupted"] = "PASSED"

        # Step 8: Encrypted PDF handling
        print("\n--- 8. Testing Encrypted PDF Handling ---")
        page.click("[title='Remove file']")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#pdf-upload-input", ENCRYPTED_PDF)
        page.wait_for_selector("#start-rotate-btn")
        page.click("#start-rotate-btn")
        page.wait_for_selector("#global-error-banner", timeout=15000)
        err_enc = page.locator("#global-error-banner").inner_text()
        print(f"Encrypted PDF error message: {err_enc}")
        assert "password" in err_enc.lower() or "encrypted" in err_enc.lower()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_error_encrypted.png"))
        page.click("text='Dismiss'")
        results["08_error_encrypted"] = "PASSED"

        # Step 9: Out of bounds custom page range
        print("\n--- 9. Testing Out of Bounds Custom Page Range ---")
        page.click("[title='Remove file']")
        page.wait_for_selector("#select-pdf-button")
        page.set_input_files("#pdf-upload-input", MULTIPAGE_PDF)
        page.wait_for_selector("#scope-custom-btn")
        page.click("#scope-custom-btn")
        page.fill("#custom-pages-input", "10-20")
        page.click("#start-rotate-btn")
        page.wait_for_selector("#global-error-banner", timeout=15000)
        err_bounds = page.locator("#global-error-banner").inner_text()
        print(f"Out of bounds error message: {err_bounds}")
        assert "exceeds total pages" in err_bounds.lower() or "out of bounds" in err_bounds.lower()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_error_out_of_bounds.png"))
        results["09_error_out_of_bounds"] = "PASSED"

        # Step 10: Regression check navigation (/merge, /split, /compress)
        print("\n--- 10. Regression Check: /merge, /split, /compress ---")
        page.goto("http://localhost:3000/merge", wait_until="networkidle")
        assert "Merge PDF Files" in page.inner_text("h1")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "10_regression_merge.png"))

        page.goto("http://localhost:3000/split", wait_until="networkidle")
        assert "Split PDF Document" in page.inner_text("h1")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "11_regression_split.png"))

        page.goto("http://localhost:3000/compress", wait_until="networkidle")
        assert "Compress PDF Document" in page.inner_text("h1")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "12_regression_compress.png"))
        results["10_regressions"] = "PASSED"

        browser.close()

    print("\n=== SUMMARY OF BROWSER VERIFICATION RESULTS ===")
    for k, v in results.items():
        print(f"{k}: {v}")
    print(f"Console errors recorded: {len(console_errors)}")
    if console_errors:
        for err in console_errors:
            print(f"  {err}")

    assert all(v == "PASSED" for v in results.values())
    print("\nALL BROWSER VERIFICATION STEPS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
