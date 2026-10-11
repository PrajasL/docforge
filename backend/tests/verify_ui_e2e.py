import os
import sys
import pypdf
from playwright.sync_api import sync_playwright

def run_browser_verification():
    scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
    fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(scratch_dir, exist_ok=True)

    pdf1_path = os.path.join(fixtures_dir, "sample_doc1.pdf")
    pdf2_path = os.path.join(fixtures_dir, "sample_doc2.pdf")
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

        # Step 1: Navigate to home
        print("[2] Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        page.screenshot(path=os.path.join(scratch_dir, "01_homepage.png"))
        assert "DocForge" in page.title() or page.locator("text=DocForge").first.is_visible()

        # Step 2: Navigate to /merge
        print("[3] Clicking Merge PDF card...")
        merge_card = page.locator("text=Merge PDF").first
        merge_card.click()
        page.wait_for_url("**/merge", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "02_merge_page.png"))
        assert page.locator("h1:has-text('Merge PDF Files')").is_visible()

        # Step 3: Upload 2 valid sample PDFs
        print("[4] Uploading sample_doc1.pdf and sample_doc2.pdf...")
        file_input = page.locator("#merge-file-input")
        file_input.set_input_files([pdf1_path, pdf2_path])
        page.wait_for_selector("[data-testid='file-item-0']", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "03_files_uploaded.png"))

        # Check filenames in list
        item0_text = page.locator("[data-testid='file-item-0']").inner_text()
        item1_text = page.locator("[data-testid='file-item-1']").inner_text()
        print(f"    Initial Item 0: {item0_text.splitlines()[0]}")
        print(f"    Initial Item 1: {item1_text.splitlines()[0]}")
        assert "sample_doc1.pdf" in item0_text
        assert "sample_doc2.pdf" in item1_text

        # Step 4: Reorder files
        print("[5] Reordering files (Moving sample_doc1.pdf down)...")
        move_down_btn = page.locator("button[aria-label='Move sample_doc1.pdf down']")
        move_down_btn.click()
        page.wait_for_timeout(500)

        item0_after = page.locator("[data-testid='file-item-0']").inner_text()
        item1_after = page.locator("[data-testid='file-item-1']").inner_text()
        print(f"    After swap Item 0: {item0_after.splitlines()[0]}")
        print(f"    After swap Item 1: {item1_after.splitlines()[0]}")
        assert "sample_doc2.pdf" in item0_after
        assert "sample_doc1.pdf" in item1_after
        page.screenshot(path=os.path.join(scratch_dir, "04_files_reordered.png"))

        # Customize output filename
        output_input = page.locator("#output-filename")
        output_input.fill("browser_e2e_merged.pdf")

        # Step 5: Click Merge button
        print("[6] Clicking Merge button and waiting for processing...")
        merge_btn = page.locator("#merge-action-btn")
        merge_btn.click()

        # Step 6: Wait for completion
        page.wait_for_selector("text=PDFs Successfully Merged!", timeout=20000)
        page.screenshot(path=os.path.join(scratch_dir, "05_merge_completed.png"))
        print("    [SUCCESS] 'PDFs Successfully Merged!' state reached.")

        # Step 7: Download result
        print("[7] Downloading resulting PDF...")
        with page.expect_download() as download_info:
            page.locator("#download-merged-pdf-btn").click()
        download = download_info.value
        downloaded_path = os.path.join(fixtures_dir, "downloaded_e2e_merged.pdf")
        download.save_as(downloaded_path)
        print(f"    Downloaded file saved to: {downloaded_path} ({os.path.getsize(downloaded_path)} bytes)")

        # Verify downloaded PDF structure & ordering
        print("[8] Validating downloaded PDF structure and page dimensions...")
        with open(downloaded_path, "rb") as f_dl:
            reader = pypdf.PdfReader(f_dl)
            total_pages = len(reader.pages)
            print(f"    Total pages in merged PDF: {total_pages}")
            assert total_pages == 5, f"Expected 5 pages, found {total_pages}"

            # Check order: doc2 (3 pages of 200x200) followed by doc1 (2 pages of 100x100)
            dims = [(p.mediabox.width, p.mediabox.height) for p in reader.pages]
            print(f"    Page dimensions: {dims}")
            assert dims[0] == (200, 200)
            assert dims[1] == (200, 200)
            assert dims[2] == (200, 200)
            assert dims[3] == (100, 100)
            assert dims[4] == (100, 100)
            print("    [VERIFIED] Pages are in exact reordered order!")

        # Step 8: Reset and test invalid file
        print("[9] Testing invalid file input rejection...")
        page.locator("button:has-text('Merge More Files')").click()
        page.wait_for_selector("#merge-file-input", state="attached", timeout=5000)

        # Upload non-pdf file
        file_input = page.locator("#merge-file-input")
        file_input.set_input_files([txt_path])
        page.wait_for_selector("text=Skipped non-PDF files: not_a_pdf.txt", timeout=5000)
        page.screenshot(path=os.path.join(scratch_dir, "06_invalid_file_error.png"))
        print("    [VERIFIED] Error banner successfully displayed for non-PDF file!")

        # Step 9: Test corrupted PDF file upload & processing error
        print("[10] Testing corrupted PDF processing error...")
        corrupt_path = os.path.join(fixtures_dir, "corrupt.pdf")
        page.locator("button:has-text('Dismiss')").click()
        file_input.set_input_files([pdf1_path, corrupt_path])
        page.wait_for_selector("[data-testid='file-item-0']", timeout=5000)
        page.locator("#merge-action-btn").click()
        page.wait_for_selector("[role='alert']", timeout=15000)
        alert_text = page.locator("[role='alert']").inner_text()
        print(f"    [VERIFIED] Error alert displayed on corrupted file: {alert_text.strip()}")
        page.screenshot(path=os.path.join(scratch_dir, "07_corrupted_file_error.png"))

        browser.close()

    print("\n--- BROWSER VERIFICATION SUMMARY ---")
    print(f"Console errors: {len(page_errors)}")
    if page_errors:
        print("Page Errors:", page_errors)
    print("ALL BROWSER UI VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_browser_verification()
