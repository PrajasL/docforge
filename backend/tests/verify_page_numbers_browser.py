import os
import sys
import pypdf
from playwright.sync_api import sync_playwright

def run_browser_verification():
    scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
    fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(scratch_dir, exist_ok=True)

    pdf3_path = os.path.join(fixtures_dir, "sample_3page.pdf")
    corrupt_path = os.path.join(fixtures_dir, "corrupt.pdf")
    encrypted_path = os.path.join(fixtures_dir, "sample_encrypted.pdf")
    txt_path = os.path.join(fixtures_dir, "not_a_pdf.txt")

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
        page.screenshot(path=os.path.join(scratch_dir, "01_pn_homepage.png"))
        assert "DocForge" in page.title() or page.locator("text=DocForge").first.is_visible()

        # Step 2: Navigate to /page-numbers
        print("[3] Clicking Page Numbers card...")
        page_numbers_card = page.locator("text=Page Numbers").first
        page_numbers_card.click()
        page.wait_for_url("**/page-numbers", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "02_pn_initial.png"))
        assert page.locator("h1:has-text('Add Page Numbers to PDF')").is_visible()

        # Step 3: Test non-PDF upload rejection
        print("[4] Testing non-PDF file upload rejection...")
        file_input = page.locator("#page-numbers-file-input")
        file_input.set_input_files(txt_path)
        page.wait_for_selector("#global-error-banner", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "03_pn_invalid_file_error.png"))
        error_text = page.locator("#global-error-banner").inner_text()
        print(f"    Validation error displayed: {error_text.strip()}")
        assert "Skipped non-PDF file" in error_text

        # Dismiss error
        page.locator("#global-error-banner button:has-text('Dismiss')").click()

        # Step 4: Upload valid 3-page PDF
        print("[5] Uploading sample_3page.pdf...")
        file_input.set_input_files(pdf3_path)
        page.wait_for_selector("#pos-bottom_center-btn", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "04_pn_file_selected.png"))
        assert page.locator("text=sample_3page.pdf").is_visible()
        assert page.locator("text=Page Number Settings").is_visible()
        assert page.locator("text=Live Page Preview").is_visible()

        # Step 5: Configure position, format, starting offsets, font size
        print("[6] Configuring page numbers settings...")
        # Position: top_right
        page.locator("#pos-top_right-btn").click()
        # Format: page_n_of_total
        page.locator("#format-page_n_of_total-btn").click()
        # Start on page: 2
        start_page_input = page.locator("#start-page-input")
        start_page_input.fill("2")
        # Starting number: 1
        start_num_input = page.locator("#start-number-input")
        start_num_input.fill("1")
        # Custom filename
        filename_input = page.locator("#output-filename-input")
        filename_input.fill("e2e_numbered_test.pdf")

        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(scratch_dir, "05_pn_custom_settings.png"))

        # Step 6: Start page numbers job
        print("[7] Submitting page numbers job to background worker...")
        start_btn = page.locator("#start-page-numbers-btn")
        start_btn.click()

        # Step 7: Wait for job completion
        print("[8] Waiting for worker completion...")
        page.wait_for_selector("text=Page Numbers Successfully Added!", timeout=25000)
        page.screenshot(path=os.path.join(scratch_dir, "06_pn_completed.png"))
        print("    Job completed successfully!")

        # Step 8: Download output PDF
        print("[9] Downloading resulting PDF...")
        with page.expect_download() as download_info:
            page.locator("#download-result-btn").click()
        download = download_info.value
        download_path = os.path.join(scratch_dir, "downloaded_numbered.pdf")
        download.save_as(download_path)
        print(f"    Saved downloaded PDF to: {download_path}")

        # Step 9: Verify downloaded PDF contents
        print("[10] Inspecting downloaded PDF with pypdf...")
        reader = pypdf.PdfReader(download_path)
        print(f"    Downloaded PDF total pages: {len(reader.pages)}")
        assert len(reader.pages) == 3

        # Page 1 (index 0) was before start_page 2: must have NO number
        p1_text = reader.pages[0].extract_text().strip()
        print(f"    Page 1 extracted text: '{p1_text}'")
        assert "Page" not in p1_text

        # Page 2 (index 1) has Page 1 of 2
        p2_text = reader.pages[1].extract_text().strip()
        print(f"    Page 2 extracted text: '{p2_text}'")
        assert "Page 1 of 2" in p2_text

        # Page 3 (index 2) has Page 2 of 2
        p3_text = reader.pages[2].extract_text().strip()
        print(f"    Page 3 extracted text: '{p3_text}'")
        assert "Page 2 of 2" in p3_text

        # Step 10: Test corrupted PDF handling
        print("[11] Testing corrupted PDF processing error flow...")
        page.locator("button:has-text('Number Another PDF')").click()
        page.wait_for_selector("#page-numbers-file-input", state="attached")
        file_input = page.locator("#page-numbers-file-input")
        file_input.set_input_files(corrupt_path)
        page.wait_for_selector("#start-page-numbers-btn", timeout=5000)
        page.locator("#start-page-numbers-btn").click()

        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "07_pn_corrupted_error.png"), full_page=True)
        corrupt_err = page.locator("#global-error-banner").inner_text()
        print(f"    Corrupted PDF error displayed: {corrupt_err.strip()}")
        assert "corrupted" in corrupt_err.lower() or "not a valid pdf" in corrupt_err.lower()

        # Step 11: Test encrypted PDF handling
        print("[12] Testing password-protected PDF processing error flow...")
        page.locator("button:has-text('Change File')").click()
        file_input = page.locator("#page-numbers-file-input")
        file_input.set_input_files(encrypted_path)
        page.wait_for_selector("#start-page-numbers-btn", timeout=5000)
        page.locator("#start-page-numbers-btn").click()

        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "08_pn_encrypted_error.png"), full_page=True)
        enc_err = page.locator("#global-error-banner").inner_text()
        print(f"    Encrypted PDF error displayed: {enc_err.strip()}")
        assert "password-protected" in enc_err.lower() or "encrypted" in enc_err.lower()

        browser.close()
        print("\nALL BROWSER WORKFLOW TESTS PASSED!")

if __name__ == "__main__":
    run_browser_verification()
