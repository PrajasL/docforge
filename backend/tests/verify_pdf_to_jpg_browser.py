import io
import os
import time
import zipfile

import pypdf
from PIL import Image
from playwright.sync_api import sync_playwright


def run_browser_verification():
    scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
    fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(scratch_dir, exist_ok=True)
    os.makedirs(fixtures_dir, exist_ok=True)

    txt_path = os.path.join(fixtures_dir, "not_a_pdf.txt")
    encrypted_path = os.path.join(fixtures_dir, "sample_encrypted.pdf")
    pdf3_path = os.path.join(scratch_dir, "browser_sample_3page.pdf")

    # Generate 3-page PDF with distinct dimensions
    writer = pypdf.PdfWriter()
    for i in range(3):
        writer.add_blank_page(width=200 + (i * 50), height=300 + (i * 50))
    writer.add_metadata({"/Title": "PDF to JPG Browser Document", "/Author": "DocForge E2E"})
    with open(pdf3_path, "wb") as f:
        writer.write(f)

    # Ensure non-pdf fixture exists
    if not os.path.exists(txt_path):
        with open(txt_path, "w") as f:
            f.write("Just text")

    # Ensure encrypted fixture exists
    if not os.path.exists(encrypted_path):
        enc_w = pypdf.PdfWriter()
        enc_w.add_blank_page(200, 300)
        enc_w.encrypt("secret123")
        with open(encrypted_path, "wb") as f:
            enc_w.write(f)

    console_logs = []
    page_errors = []

    print("=== STARTING BROWSER E2E VERIFICATION FOR PART 15 - PDF TO JPG ===")
    with sync_playwright() as p:
        print("[Step 1] Launching MS Edge browser...")
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # 1. Homepage tool card check
        print("[Step 2] Visiting DocForge homepage...")
        page.goto("http://localhost:3000")
        page.wait_for_selector("text=DocForge")
        pdf_to_jpg_card = page.locator("text=PDF to JPG")
        assert pdf_to_jpg_card.is_visible(), "PDF to JPG card not visible on homepage"
        print("  [PASS] PDF to JPG tool card verified on homepage.")

        # 2. Navigate to /pdf-to-jpg
        print("[Step 3] Navigating to /pdf-to-jpg...")
        page.goto("http://localhost:3000/pdf-to-jpg")
        page.wait_for_selector("text=Convert PDF to JPG Images")
        print("  [PASS] PDF to JPG page loaded successfully.")

        # 3. Test non-PDF rejection
        print("[Step 4] Testing non-PDF file upload rejection...")
        file_input = page.locator("#pdf-upload-input")
        file_input.set_input_files(txt_path)
        page.wait_for_selector("#global-error-banner", timeout=5000)
        err_msg = page.locator("#global-error-banner").inner_text()
        assert "Only PDF files are supported" in err_msg
        print(f"  [PASS] Non-PDF rejected with banner: {err_msg.strip()}")

        # Dismiss error
        page.locator("#global-error-banner button:has-text('Dismiss')").click()

        # 4. Upload 3-page PDF
        print("[Step 5] Uploading 3-page PDF...")
        file_input.set_input_files(pdf3_path)
        page.wait_for_selector("text=browser_sample_3page.pdf")
        page.wait_for_selector("#detected-pages-badge", timeout=8000)
        badge_text = page.locator("#detected-pages-badge").inner_text()
        assert "3 pages detected" in badge_text
        print(f"  [PASS] Page count detected: {badge_text}")

        # 5. Toggle resolution to High (300 DPI)
        print("[Step 6] Configuring 300 DPI high resolution...")
        card_300 = page.locator("#dpi-300-card")
        card_300.click()
        time.sleep(0.3)
        assert "border-amber-600" in (card_300.get_attribute("class") or "")
        print("  [PASS] 300 DPI resolution selected.")

        # 6. Set quality to 95%
        print("[Step 7] Setting maximum quality (95%)...")
        q95_btn = page.locator("#quality-95-btn")
        q95_btn.click()
        assert page.locator("span:has-text('95%')").first.is_visible()
        print("  [PASS] Quality set to 95%.")

        # 7. Set custom output filename
        print("[Step 8] Setting custom output filename...")
        filename_input = page.locator("#output-filename-input")
        filename_input.fill("browser_e2e_gallery.zip")
        print("  [PASS] Custom filename configured.")

        # 8. Start conversion
        print("[Step 9] Submitting conversion job...")
        submit_btn = page.locator("#pdf-to-jpg-submit-btn")
        submit_btn.click()

        print("  Waiting for conversion completion...")
        page.wait_for_selector("#download-result-btn", timeout=30000)
        print("  [PASS] Conversion finished! Download button displayed.")

        # 9. Verify result summary stats
        assert page.get_by_text("3 Pages", exact=True).is_visible()
        assert page.get_by_text("300 DPI", exact=True).is_visible()
        print("  [PASS] Result summary verified (3 Pages, 300 DPI).")

        # 10. Download output ZIP archive
        print("[Step 10] Downloading converted ZIP archive...")
        with page.expect_download() as download_info:
            page.locator("#download-result-btn").click()
        download = download_info.value
        download_path = os.path.join(scratch_dir, "downloaded_pdf_to_jpg.zip")
        download.save_as(download_path)
        print(f"  [PASS] Downloaded archive saved to: {download_path}")

        # 11. Inspect ZIP archive contents
        print("[Step 11] Inspecting ZIP archive contents...")
        with zipfile.ZipFile(download_path, "r") as z:
            names = z.namelist()
            assert len(names) == 3, f"Expected 3 images, got {len(names)}: {names}"
            assert names == ["page_01.jpg", "page_02.jpg", "page_03.jpg"]

            # Inspect page 1 dimensions: 200 pt * (300/72) = 833 px, 300 pt * (300/72) = 1250 px
            with Image.open(io.BytesIO(z.read("page_01.jpg"))) as img1:
                assert img1.format == "JPEG"
                assert abs(img1.width - 833) <= 3
                assert abs(img1.height - 1250) <= 3

            # Inspect page 3 dimensions: 300 pt * (300/72) = 1250 px, 400 pt * (300/72) = 1667 px
            with Image.open(io.BytesIO(z.read("page_03.jpg"))) as img3:
                assert img3.format == "JPEG"
                assert abs(img3.width - 1250) <= 3
                assert abs(img3.height - 1667) <= 3

        print("  [PASS] Downloaded ZIP verified: 3 JPEG files with matching 300 DPI dimensions!")

        # 12. Check all 11 tool routes for regressions
        print("[Step 12] Checking all tool route health regressions...")
        routes = [
            ("/merge", "Merge PDF"),
            ("/split", "Split PDF"),
            ("/compress", "Compress PDF"),
            ("/rotate", "Rotate PDF"),
            ("/watermark", "Watermark"),
            ("/page-numbers", "Page Numbers"),
            ("/protect", "Protect PDF"),
            ("/unlock", "Unlock"),
            ("/extract-pages", "Extract Pages"),
            ("/organize-pdf", "Organize PDF"),
            ("/pdf-to-jpg", "PDF to JPG"),
        ]

        for route, title in routes:
            resp = page.goto(f"http://localhost:3000{route}")
            assert resp.status == 200, f"Route {route} returned status {resp.status}"
            assert page.locator(f"text={title}").first.is_visible(), f"Route {route} missing title '{title}'"
            print(f"  [PASS] Route {route} healthy (200 OK, title contains '{title}')")

        context.close()
        browser.close()

    print("=== BROWSER E2E VERIFICATION FOR PDF TO JPG COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_browser_verification()
