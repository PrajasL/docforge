import os
import sys
import pypdf
from playwright.sync_api import sync_playwright

def run_browser_verification():
    scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
    fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(scratch_dir, exist_ok=True)
    os.makedirs(fixtures_dir, exist_ok=True)

    txt_path = os.path.join(fixtures_dir, "not_a_pdf.txt")
    corrupt_path = os.path.join(fixtures_dir, "corrupt.pdf")
    encrypted_path = os.path.join(fixtures_dir, "sample_encrypted.pdf")
    pdf5_path = os.path.join(scratch_dir, "browser_sample_5page.pdf")

    # Generate dedicated 5-page PDF fixture with varying dimensions
    writer = pypdf.PdfWriter()
    for i in range(5):
        writer.add_blank_page(width=200 + (i * 50), height=300 + (i * 50))
    writer.add_metadata({"/Title": "DocForge Page Extraction Vault", "/Author": "Playwright Suite"})
    with open(pdf5_path, "wb") as f:
        writer.write(f)

    console_logs = []
    page_errors = []

    with sync_playwright() as p:
        print("[1] Launching MS Edge browser...")
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # Step 1: Navigate to homepage
        print("[2] Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        page.screenshot(path=os.path.join(scratch_dir, "01_extract_homepage.png"))
        assert "DocForge" in page.title() or page.locator("text=DocForge").first.is_visible()

        # Step 2: Navigate to /extract-pages
        print("[3] Clicking Extract Pages card...")
        extract_card = page.locator("text=Extract Pages").first
        extract_card.click()
        page.wait_for_url("**/extract-pages", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "02_extract_initial.png"))
        assert page.locator("h1:has-text('Extract Pages from PDF')").is_visible()

        # Step 3: Test non-PDF upload rejection
        print("[4] Testing non-PDF file upload rejection...")
        file_input = page.locator("#pdf-upload-input")
        file_input.set_input_files(txt_path)
        page.wait_for_selector("#global-error-banner", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "03_extract_invalid_file_error.png"))
        error_text = page.locator("#global-error-banner").inner_text()
        print(f"    Validation error displayed: {error_text.strip()}")
        assert "Skipped non-PDF file" in error_text

        # Dismiss error
        page.locator("#global-error-banner button:has-text('Dismiss')").click()

        # Step 4: Upload valid 5-page PDF
        print("[5] Uploading browser_sample_5page.pdf...")
        file_input.set_input_files(pdf5_path)
        page.wait_for_selector("#page-ranges-input", timeout=5000)
        page.wait_for_selector("#detected-pages-badge", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "04_extract_file_selected.png"))
        assert page.locator("text=browser_sample_5page.pdf").is_visible()

        # Step 5: Test client-side out-of-bounds range validation
        print("[6] Testing out-of-bounds page range rejection...")
        ranges_input = page.locator("#page-ranges-input")
        ranges_input.fill("1, 8")
        page.locator("#extract-submit-btn").click()
        page.wait_for_selector("#global-error-banner", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "05_extract_out_of_bounds_error.png"))
        oob_text = page.locator("#global-error-banner").inner_text()
        print(f"    Out of bounds error displayed: {oob_text.strip()}")
        assert "out of bounds" in oob_text.lower() or "exceeds" in oob_text.lower()

        # Dismiss error
        page.locator("#global-error-banner button:has-text('Dismiss')").click()

        # Step 6: Enter valid custom non-sequential ranges (4, 2-3, 1) and output filename
        print("[7] Configuring custom ranges: '4, 2-3, 1'...")
        ranges_input.fill("4, 2-3, 1")
        filename_input = page.locator("#output-filename-input")
        filename_input.fill("browser_extracted_custom.pdf")
        page.screenshot(path=os.path.join(scratch_dir, "06_extract_configured.png"))

        # Step 7: Submit extraction job to background worker
        print("[8] Submitting extraction job to Celery worker...")
        page.locator("#extract-submit-btn").click()

        # Step 8: Wait for worker completion
        print("[9] Waiting for worker completion...")
        page.wait_for_selector("text=Pages Successfully Extracted!", timeout=25000)
        page.screenshot(path=os.path.join(scratch_dir, "07_extract_completed.png"))
        print("    Job completed successfully!")
        assert page.locator("text=browser_extracted_custom.pdf").is_visible()
        assert page.locator("text=4 Pages").is_visible()

        # Step 9: Download resulting PDF
        print("[10] Downloading extracted PDF result...")
        download_btn = page.locator("#download-result-btn")
        with page.expect_download() as download_info:
            download_btn.click()

        download = download_info.value
        downloaded_path = os.path.join(scratch_dir, "downloaded_extracted_custom.pdf")
        download.save_as(downloaded_path)
        print(f"    Downloaded result saved to: {downloaded_path}")
        assert os.path.exists(downloaded_path)
        assert os.path.getsize(downloaded_path) > 0

        # Step 10: Inspect downloaded PDF with pypdf
        print("[11] Inspecting extracted PDF structure with pypdf...")
        reader = pypdf.PdfReader(downloaded_path)
        assert len(reader.pages) == 4, f"Expected 4 pages, got {len(reader.pages)}"
        # Original page 4: 350x450
        assert float(reader.pages[0].mediabox.width) == 350.0
        assert float(reader.pages[0].mediabox.height) == 450.0
        # Original page 2: 250x350
        assert float(reader.pages[1].mediabox.width) == 250.0
        assert float(reader.pages[1].mediabox.height) == 350.0
        # Original page 3: 300x400
        assert float(reader.pages[2].mediabox.width) == 300.0
        assert float(reader.pages[2].mediabox.height) == 400.0
        # Original page 1: 200x300
        assert float(reader.pages[3].mediabox.width) == 200.0
        assert float(reader.pages[3].mediabox.height) == 300.0
        print("    [VERIFIED] Exact custom non-sequential ordering (4, 2, 3, 1) confirmed!")

        # Step 11: Test 'Extract All Pages' mode
        print("[12] Testing Extract All Pages mode...")
        page.locator("#extract-another-btn").click()
        page.wait_for_selector("#select-file-btn", timeout=5000)
        file_input.set_input_files(pdf5_path)
        page.wait_for_selector("#extract-all-toggle-btn", timeout=5000)
        page.locator("#extract-all-toggle-btn").click()
        page.locator("#output-filename-input").fill("browser_all_pages.pdf")
        page.screenshot(path=os.path.join(scratch_dir, "08_extract_all_mode.png"))

        page.locator("#extract-submit-btn").click()
        page.wait_for_selector("text=Pages Successfully Extracted!", timeout=25000)
        page.screenshot(path=os.path.join(scratch_dir, "09_extract_all_completed.png"))
        assert page.get_by_text("5 Pages", exact=True).is_visible()

        with page.expect_download() as dl_info2:
            page.locator("#download-result-btn").click()
        dl2 = dl_info2.value
        all_pages_path = os.path.join(scratch_dir, "downloaded_all_pages.pdf")
        dl2.save_as(all_pages_path)
        reader_all = pypdf.PdfReader(all_pages_path)
        assert len(reader_all.pages) == 5
        print("    [VERIFIED] Extract All Pages produced 5 pages!")

        # Step 12: Test Encrypted PDF Server Rejection
        print("[13] Testing encrypted PDF rejection flow...")
        page.locator("#extract-another-btn").click()
        page.wait_for_selector("#select-file-btn", timeout=5000)
        file_input.set_input_files(encrypted_path)
        page.wait_for_selector("#extract-submit-btn", timeout=5000)
        page.locator("#extract-submit-btn").click()
        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "10_extract_encrypted_error.png"))
        enc_err = page.locator("#global-error-banner").inner_text()
        print(f"    Encrypted error displayed: {enc_err.strip()}")
        assert "password-protected" in enc_err

        browser.close()

    print("\n[SUCCESS] Extract Pages Browser Verification Passed 100%!")
    print(f"Total console logs: {len(console_logs)}")
    print(f"Total page errors: {len(page_errors)}")

if __name__ == "__main__":
    run_browser_verification()
