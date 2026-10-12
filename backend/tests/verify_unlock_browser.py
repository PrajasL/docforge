import os

import pypdf
from playwright.sync_api import sync_playwright


def run_unlock_browser_verification():
    scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
    fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(scratch_dir, exist_ok=True)
    os.makedirs(fixtures_dir, exist_ok=True)

    # Prepare fixtures
    pdf3_path = os.path.join(fixtures_dir, "sample_3page.pdf")
    txt_path = os.path.join(fixtures_dir, "not_a_pdf.txt")
    locked_pdf_path = os.path.join(fixtures_dir, "unlock_test_locked.pdf")
    os.path.join(fixtures_dir, "corrupt.pdf")

    KNOWN_PASSWORD = "UnlockBrowserTest2026!"

    # Create password-protected PDF with known password using AES-256
    writer = pypdf.PdfWriter()
    for i in range(3):
        writer.add_blank_page(width=450, height=650)
    writer.add_metadata({"/Title": "DocForge Browser Vault", "/Author": "Playwright Suite"})
    writer.encrypt(user_password=KNOWN_PASSWORD, algorithm="AES-256")
    with open(locked_pdf_path, "wb") as f:
        writer.write(f)

    print(f"[*] Prepared encrypted test fixture at: {locked_pdf_path} (Password: {KNOWN_PASSWORD})")

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
        page.screenshot(path=os.path.join(scratch_dir, "01_unlock_homepage.png"))
        assert page.locator("text=DocForge").first.is_visible()

        # Verify Unlock PDF card is on homepage
        unlock_card = page.locator("text=Unlock PDF").first
        assert unlock_card.is_visible(), "Unlock PDF card not found on homepage"

        # Step 2: Navigate to /unlock
        print("[3] Clicking Unlock PDF card...")
        unlock_card.click()
        page.wait_for_url("**/unlock", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "02_unlock_initial.png"))
        assert page.locator("h1:has-text('Unlock Password-Protected PDF')").is_visible()

        # Step 3: Test non-PDF file upload rejection
        print("[4] Testing non-PDF file upload rejection...")
        file_input = page.locator("#pdf-upload-input")
        file_input.set_input_files(txt_path)
        page.wait_for_selector("#global-error-banner", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "03_unlock_invalid_file_error.png"))
        err_banner = page.locator("#global-error-banner").inner_text()
        print(f"    Validation error displayed: {err_banner.strip()}")
        assert "Skipped non-PDF file" in err_banner

        # Dismiss error
        page.locator("#global-error-banner button:has-text('Dismiss')").click()

        # Step 4: Test unencrypted PDF rejection
        print("[5] Testing unencrypted PDF rejection...")
        file_input.set_input_files(pdf3_path)
        page.wait_for_selector("#password-input", timeout=5000)
        page.locator("#password-input").fill("AnyPassword123")
        page.screenshot(path=os.path.join(scratch_dir, "04_unlock_unencrypted_uploaded.png"))
        page.locator("#unlock-submit-btn").click()

        # Server should reject unencrypted file with NOT_ENCRYPTED error
        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "05_unlock_unencrypted_error.png"))
        unencrypted_err = page.locator("#global-error-banner").inner_text()
        print(f"    Unencrypted error displayed: {unencrypted_err.strip()}")
        assert "not password-protected" in unencrypted_err

        # Reset selection
        print("[6] Resetting file selection...")
        page.locator("button:has-text('Change File')").click()
        page.wait_for_selector("#select-file-btn", timeout=5000)

        # Step 5: Upload valid protected PDF
        print("[7] Uploading unlock_test_locked.pdf...")
        file_input.set_input_files(locked_pdf_path)
        page.wait_for_selector("#password-input", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "06_unlock_protected_file_selected.png"))
        assert page.locator("text=unlock_test_locked.pdf").is_visible()

        # Step 6: Test password visibility toggle
        print("[8] Testing password input and visibility toggle...")
        pwd_input = page.locator("#password-input")
        pwd_input.fill(KNOWN_PASSWORD)
        toggle_btn = page.locator("#toggle-password-visibility-btn")
        toggle_btn.click()
        assert pwd_input.get_attribute("type") == "text"
        page.screenshot(path=os.path.join(scratch_dir, "07_unlock_password_visible.png"))
        toggle_btn.click()
        assert pwd_input.get_attribute("type") == "password"

        # Step 7: Test incorrect password rejection
        print("[9] Testing incorrect password rejection...")
        pwd_input.fill("WrongPasswordAttempt999")
        page.locator("#unlock-submit-btn").click()
        page.wait_for_selector("#global-error-banner", timeout=15000)
        page.screenshot(path=os.path.join(scratch_dir, "08_unlock_wrong_password_error.png"))
        wrong_pw_err = page.locator("#global-error-banner").inner_text()
        print(f"    Wrong password error displayed: {wrong_pw_err.strip()}")
        assert "incorrect" in wrong_pw_err.lower() or "failed" in wrong_pw_err.lower()

        # Step 8: Enter correct password and custom output filename
        print("[10] Entering correct password and submitting unlock job...")
        pwd_input.fill(KNOWN_PASSWORD)
        filename_input = page.locator("#output-filename-input")
        filename_input.fill("e2e_unlocked_result.pdf")
        page.screenshot(path=os.path.join(scratch_dir, "09_unlock_configured.png"))

        page.locator("#unlock-submit-btn").click()

        # Step 9: Wait for worker completion
        print("[11] Waiting for Celery background worker completion...")
        page.wait_for_selector("text=PDF Successfully Unlocked!", timeout=30000)
        page.screenshot(path=os.path.join(scratch_dir, "10_unlock_completed.png"))
        print("    Job completed successfully!")

        # Verify result card data
        assert page.locator("text=e2e_unlocked_result.pdf").is_visible()
        assert page.locator("text=Unrestricted").is_visible()

        # Step 10: Download unlocked PDF
        print("[12] Downloading unlocked PDF result...")
        download_btn = page.locator("#download-result-btn")
        with page.expect_download() as download_info:
            download_btn.click()

        download = download_info.value
        downloaded_path = os.path.join(scratch_dir, "downloaded_unlocked_result.pdf")
        download.save_as(downloaded_path)
        print(f"    Downloaded result saved to: {downloaded_path}")
        assert os.path.exists(downloaded_path)
        assert os.path.getsize(downloaded_path) > 0

        # Step 11: PyPDF Content Verification
        print("[13] Verifying output PDF with pypdf...")
        unlocked_reader = pypdf.PdfReader(downloaded_path)
        print(f"    is_encrypted: {unlocked_reader.is_encrypted}")
        print(f"    page count: {len(unlocked_reader.pages)}")

        # Crucial: Must NOT be encrypted
        assert unlocked_reader.is_encrypted is False, "Output PDF is still encrypted!"
        assert len(unlocked_reader.pages) == 3, f"Expected 3 pages, found {len(unlocked_reader.pages)}"
        for idx, pg in enumerate(unlocked_reader.pages):
            assert float(pg.mediabox.width) == 450.0
            assert float(pg.mediabox.height) == 650.0
            print(f"    Page {idx + 1} verified: {pg.mediabox.width}x{pg.mediabox.height}")

        # Metadata preservation check
        assert unlocked_reader.metadata is not None
        assert unlocked_reader.metadata.title == "DocForge Browser Vault"
        print(f"    Preserved metadata title: {unlocked_reader.metadata.title}")

        browser.close()

    print("\n[SUCCESS] Browser End-to-End Verification Passed 100%!")
    print(f"Total console logs: {len(console_logs)}")
    print(f"Total page errors: {len(page_errors)}")
    if page_errors:
        print("Page errors:", page_errors)

if __name__ == "__main__":
    run_unlock_browser_verification()
