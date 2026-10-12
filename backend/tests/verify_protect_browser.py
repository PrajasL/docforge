import os

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
        page.screenshot(path=os.path.join(scratch_dir, "01_protect_homepage.png"))
        assert "DocForge" in page.title() or page.locator("text=DocForge").first.is_visible()

        # Step 2: Navigate to /protect
        print("[3] Clicking Protect PDF card...")
        protect_card = page.locator("text=Protect PDF").first
        protect_card.click()
        page.wait_for_url("**/protect", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "02_protect_initial.png"))
        assert page.locator("h1:has-text('Protect PDF with Password')").is_visible()

        # Step 3: Test non-PDF upload rejection
        print("[4] Testing non-PDF file upload rejection...")
        file_input = page.locator("#protect-file-input")
        file_input.set_input_files(txt_path)
        page.wait_for_selector("#global-error-banner", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "03_protect_invalid_file_error.png"))
        error_text = page.locator("#global-error-banner").inner_text()
        print(f"    Validation error displayed: {error_text.strip()}")
        assert "Skipped non-PDF file" in error_text

        # Dismiss error
        page.locator("#global-error-banner button:has-text('Dismiss')").click()

        # Step 4: Upload valid 3-page PDF
        print("[5] Uploading sample_3page.pdf...")
        file_input.set_input_files(pdf3_path)
        page.wait_for_selector("#password-input", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "04_protect_file_selected.png"))
        assert page.locator("text=sample_3page.pdf").is_visible()
        assert page.locator("text=Set Document Password").is_visible()

        # Step 5: Test password visibility toggle and mismatch detection
        print("[6] Testing password fields, visibility toggle, and match indicator...")
        pwd_input = page.locator("#password-input")
        confirm_input = page.locator("#confirm-password-input")

        # Type mismatched passwords
        pwd_input.fill("SuperSecret2026!")
        confirm_input.fill("WrongMismatchPass")
        page.wait_for_timeout(200)
        assert page.locator("text=Passwords do not match").is_visible()

        # Test show/hide password toggles
        toggle_pw = page.locator("#toggle-password-visibility-btn")
        toggle_pw.click()
        assert pwd_input.get_attribute("type") == "text"
        toggle_pw.click()
        assert pwd_input.get_attribute("type") == "password"

        # Correct confirm password
        confirm_input.fill("SuperSecret2026!")
        page.wait_for_timeout(200)
        assert page.locator("text=Passwords match").is_visible()

        # Custom filename
        filename_input = page.locator("#output-filename-input")
        filename_input.fill("e2e_protected_test.pdf")

        page.screenshot(path=os.path.join(scratch_dir, "05_protect_configured.png"))

        # Step 6: Start protect job
        print("[7] Submitting encryption job to background worker...")
        start_btn = page.locator("#start-protect-btn")
        start_btn.click()

        # Step 7: Wait for job completion
        print("[8] Waiting for worker completion...")
        page.wait_for_selector("text=PDF Successfully Protected!", timeout=25000)
        page.screenshot(path=os.path.join(scratch_dir, "06_protect_completed.png"))
        print("    Job completed successfully!")

        # Step 8: Download output PDF
        print("[9] Downloading resulting PDF...")
        with page.expect_download() as download_info:
            page.locator("#download-result-btn").click()
        download = download_info.value
        download_path = os.path.join(scratch_dir, "downloaded_protected.pdf")
        download.save_as(download_path)
        print(f"    Saved downloaded PDF to: {download_path}")

        # Step 9: Verify downloaded PDF contents and encryption
        print("[10] Inspecting downloaded PDF with pypdf...")
        reader = pypdf.PdfReader(download_path)
        print(f"    is_encrypted: {reader.is_encrypted}")
        assert reader.is_encrypted is True

        # Decrypt with wrong password fails
        dec_wrong = reader.decrypt("WrongPassword123")
        assert dec_wrong == 0
        print("    Wrong password successfully rejected by PDF reader.")

        # Decrypt with correct password succeeds
        dec_correct = reader.decrypt("SuperSecret2026!")
        assert dec_correct != 0
        print(f"    Correct password unlocked document (result code: {dec_correct})")
        assert len(reader.pages) == 3
        print(f"    Total pages in protected PDF: {len(reader.pages)}")

        # Step 10: Test corrupted PDF handling
        print("[11] Testing corrupted PDF processing error flow...")
        page.locator("button:has-text('Protect Another PDF')").click()
        page.wait_for_selector("#protect-file-input", state="attached")
        file_input = page.locator("#protect-file-input")
        file_input.set_input_files(corrupt_path)
        page.wait_for_selector("#password-input", timeout=5000)
        page.locator("#password-input").fill("AnyPass123!")
        page.locator("#confirm-password-input").fill("AnyPass123!")
        page.locator("#start-protect-btn").click()

        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "07_protect_corrupted_error.png"), full_page=True)
        corrupt_err = page.locator("#global-error-banner").inner_text()
        print(f"    Corrupted PDF error displayed: {corrupt_err.strip()}")
        assert "corrupted" in corrupt_err.lower() or "not a valid pdf" in corrupt_err.lower()

        # Step 11: Test already-encrypted PDF handling
        print("[12] Testing already password-protected PDF processing error flow...")
        if page.locator("#global-error-banner button:has-text('Dismiss')").is_visible():
            page.locator("#global-error-banner button:has-text('Dismiss')").click()
        page.locator("button:has-text('Change File')").click()
        page.wait_for_selector("#protect-file-input", state="attached")
        file_input = page.locator("#protect-file-input")
        file_input.set_input_files(encrypted_path)
        page.wait_for_selector("#password-input", timeout=5000)
        page.wait_for_timeout(200)
        page.locator("#password-input").fill("AnyPass123!")
        page.locator("#confirm-password-input").fill("AnyPass123!")
        page.wait_for_timeout(300)
        page.locator("#start-protect-btn").click()

        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "08_protect_already_encrypted_error.png"), full_page=True)
        enc_err = page.locator("#global-error-banner").inner_text()
        print(f"    Already encrypted PDF error displayed: {enc_err.strip()}")
        assert "already password-protected" in enc_err.lower()

        browser.close()
        print("\nALL BROWSER WORKFLOW TESTS PASSED!")

if __name__ == "__main__":
    run_browser_verification()
