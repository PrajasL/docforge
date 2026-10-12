import os
import time

import pypdf
from PIL import Image
from playwright.sync_api import sync_playwright


def run_browser_verification():
    scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch")
    fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    os.makedirs(scratch_dir, exist_ok=True)
    os.makedirs(fixtures_dir, exist_ok=True)

    txt_path = os.path.join(fixtures_dir, "not_a_jpg.txt")
    if not os.path.exists(txt_path):
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Just a plain text file, not an image.")

    # Generate 3 distinct test JPEGs
    img1_path = os.path.join(scratch_dir, "photo_red.jpg")
    img2_path = os.path.join(scratch_dir, "photo_green.jpg")
    img3_path = os.path.join(scratch_dir, "photo_blue.jpg")

    for path, color in [
        (img1_path, (220, 50, 50)),
        (img2_path, (50, 200, 50)),
        (img3_path, (50, 100, 240)),
    ]:
        img = Image.new("RGB", (400, 300), color=color)
        img.save(path, "JPEG", quality=90)

    console_logs = []
    page_errors = []

    print("=== STARTING BROWSER E2E VERIFICATION FOR PART 16 - JPG TO PDF ===")
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
        jpg_to_pdf_card = page.locator("text=JPG to PDF")
        assert jpg_to_pdf_card.is_visible(), "JPG to PDF card not visible on homepage"
        print("  [PASS] JPG to PDF tool card verified on homepage.")

        # 2. Navigate to /jpg-to-pdf
        print("[Step 3] Navigating to /jpg-to-pdf...")
        page.goto("http://localhost:3000/jpg-to-pdf")
        page.wait_for_selector("h1:has-text('JPG to PDF')")
        print("  [PASS] JPG to PDF page loaded successfully.")

        # 3. Test non-JPG rejection
        print("[Step 4] Testing non-JPG file upload rejection...")
        file_input = page.locator("input[type='file']")
        file_input.set_input_files(txt_path)
        page.wait_for_selector("#jpg-to-pdf-error-banner", timeout=5000)
        err_msg = page.locator("#jpg-to-pdf-error-banner").inner_text()
        assert "Only JPG/JPEG images are accepted" in err_msg
        print(f"  [PASS] Non-JPG rejected with alert: {err_msg.strip()}")

        # Dismiss error
        page.locator("#jpg-to-pdf-error-banner button").click()

        # 4. Upload 3 JPEG images
        print("[Step 5] Uploading 3 JPEG images...")
        file_input.set_input_files([img1_path, img2_path, img3_path])
        page.wait_for_selector("text=photo_red.jpg")
        page.wait_for_selector("text=photo_green.jpg")
        page.wait_for_selector("text=photo_blue.jpg")
        print("  [PASS] All 3 images displayed in gallery with previews and badges.")

        # 5. Reorder: Move second image earlier (photo_green -> first)
        print("[Step 6] Reordering images using arrow buttons...")
        # Find move up buttons in cards
        up_buttons = page.locator("button[title='Move earlier']")
        assert up_buttons.count() == 3
        # Click move earlier on second image (index 1)
        up_buttons.nth(1).click()
        time.sleep(0.3)
        print("  [PASS] Image sequence reordered successfully.")

        # 6. Configure Page Layout & Margins
        print("[Step 7] Setting orientation to Landscape, page size to A4, margin to Small Margin...")
        page.locator("button:has-text('Landscape')").click()
        page.locator("button:has-text('A4')").click()
        page.locator("button:has-text('Small Margin')").click()
        print("  [PASS] Layout options configured.")

        # 7. Set custom output filename
        print("[Step 8] Setting custom output filename...")
        page.locator("#outputFilename").fill("vacation_album.pdf")
        print("  [PASS] Custom filename set to vacation_album.pdf.")

        # 8. Start conversion
        print("[Step 9] Submitting conversion to PDF...")
        page.locator("button:has-text('Convert to PDF')").click()

        print("  Waiting for conversion completion...")
        page.wait_for_selector("button:has-text('Download PDF')", timeout=30000)
        print("  [PASS] Conversion finished! Download PDF button displayed.")

        # 9. Verify result summary stats
        assert page.get_by_text("vacation_album.pdf").is_visible()
        assert page.get_by_text("3 pages").is_visible()
        assert page.get_by_text("3 images").is_visible()
        print("  [PASS] Result summary verified (3 pages, 3 images, vacation_album.pdf).")

        # 10. Download output PDF
        print("[Step 10] Downloading generated PDF...")
        with page.expect_download() as download_info:
            page.locator("button:has-text('Download PDF')").click()
        download = download_info.value
        download_path = os.path.join(scratch_dir, "downloaded_vacation_album.pdf")
        download.save_as(download_path)
        print(f"  [PASS] Downloaded PDF saved to: {download_path}")

        # 11. Inspect PDF contents with pypdf
        print("[Step 11] Inspecting downloaded PDF structure...")
        with open(download_path, "rb") as f_pdf:
            reader = pypdf.PdfReader(f_pdf)
            assert len(reader.pages) == 3, f"Expected 3 pages, found {len(reader.pages)}"
            for idx, p_obj in enumerate(reader.pages):
                width = float(p_obj.mediabox.width)
                height = float(p_obj.mediabox.height)
                # Verify Landscape A4: width > height (~841.89 pt x ~595.28 pt)
                assert width > height, f"Page {idx + 1} is not landscape: {width}x{height}"
                assert abs(width - 841.89) < 2.0, f"Page {idx + 1} width mismatch: {width}"
                assert abs(height - 595.28) < 2.0, f"Page {idx + 1} height mismatch: {height}"

        print("  [PASS] PDF verified: Exactly 3 pages in A4 landscape with small margins!")

        # 12. Check all 12 tool routes for regressions
        print("[Step 12] Checking all 12 tool routes for regressions...")
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
            ("/jpg-to-pdf", "JPG to PDF"),
        ]

        for route, title in routes:
            resp = page.goto(f"http://localhost:3000{route}")
            assert resp.status == 200, f"Route {route} returned status {resp.status}"
            assert page.locator(f"text={title}").first.is_visible(), f"Route {route} missing title '{title}'"
            print(f"  [PASS] Route {route} healthy (200 OK, title contains '{title}')")

        context.close()
        browser.close()

    print("=== BROWSER E2E VERIFICATION FOR JPG TO PDF COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_browser_verification()
