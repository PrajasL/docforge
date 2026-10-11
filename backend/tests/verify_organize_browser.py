import asyncio
import io
import os
import tempfile
import pypdf
from playwright.async_api import async_playwright


def create_test_pdf(num_pages: int = 4) -> str:
    writer = pypdf.PdfWriter()
    for i in range(num_pages):
        width = 200 + i * 50
        height = 300 + i * 50
        writer.add_blank_page(width=width, height=height)
    writer.add_metadata({"/Title": "Browser Verification Document", "/Author": "DocForge E2E"})
    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    writer.write(temp_file)
    temp_file.close()
    return temp_file.name


def create_encrypted_pdf() -> str:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt(user_password="secret_password", algorithm="AES-256")
    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    writer.write(temp_file)
    temp_file.close()
    return temp_file.name


async def run_browser_verification():
    print("=== STARTING BROWSER E2E VERIFICATION FOR PART 14 - ORGANIZE PDF ===")

    test_pdf_path = create_test_pdf(4)
    encrypted_pdf_path = create_encrypted_pdf()
    dummy_txt_path = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
    with open(dummy_txt_path, "w") as f:
        f.write("This is not a PDF file.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page()

        # Step 1: Homepage Verification
        print("[Step 1] Visiting DocForge homepage...")
        await page.goto("http://localhost:3000/")
        await page.wait_for_selector("text=DocForge")
        organize_link = await page.query_selector('a[href="/organize-pdf"]')
        assert organize_link is not None, "Organize PDF card link not found on homepage!"
        print("  [PASS] Organize PDF tool card verified on homepage.")

        # Step 2: Open /organize-pdf
        print("[Step 2] Navigating to /organize-pdf...")
        await page.goto("http://localhost:3000/organize-pdf")
        heading = await page.text_content("h1")
        assert "Organize PDF" in heading, f"Unexpected heading: {heading}"
        print("  [PASS] Organize PDF page loaded successfully.")

        # Step 3: Test non-PDF upload error
        print("[Step 3] Testing non-PDF file upload rejection...")
        file_input = await page.query_selector("#pdf-upload-input")
        assert file_input is not None
        await file_input.set_input_files(dummy_txt_path)
        await page.wait_for_selector("#global-error-banner")
        banner_text = await page.text_content("#global-error-banner")
        assert "Skipped non-PDF file" in banner_text, f"Unexpected error text: {banner_text}"
        print(f"  [PASS] Non-PDF rejected with banner: {banner_text.strip()}")

        # Dismiss error banner
        dismiss_btn = await page.query_selector("#global-error-banner button")
        if dismiss_btn:
            await dismiss_btn.click()
            await asyncio.sleep(0.3)

        # Step 4: Upload valid 4-page PDF
        print("[Step 4] Uploading 4-page PDF and waiting for thumbnails grid...")
        await file_input.set_input_files(test_pdf_path)
        await page.wait_for_selector("#pages-grid", timeout=10000)
        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        assert len(page_cards) == 4, f"Expected 4 page cards in grid, found {len(page_cards)}"
        print(f"  [PASS] PDF loaded into visual editor with {len(page_cards)} pages.")

        # Step 5: Test Rotate Page 1 (+90 deg)
        print("[Step 5] Testing rotate button on Page 1...")
        rotate_btn = await page_cards[0].query_selector('[data-testid="rotate-page-btn"]')
        assert rotate_btn is not None
        await rotate_btn.click()
        await page.wait_for_selector("text=+90")
        print("  [PASS] Page 1 rotated to +90 deg.")

        # Step 6: Test Duplicate Page 2
        print("[Step 6] Testing duplicate button on Page 2...")
        duplicate_btn = await page_cards[1].query_selector('[data-testid="duplicate-page-btn"]')
        assert duplicate_btn is not None
        await duplicate_btn.click()
        await asyncio.sleep(0.5)
        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        assert len(page_cards) == 5, f"Expected 5 page cards after duplication, found {len(page_cards)}"
        print("  [PASS] Page 2 duplicated. Total pages now 5.")

        # Step 7: Test Delete Page 4
        print("[Step 7] Testing delete button on Page 4...")
        delete_btn = await page_cards[3].query_selector('[data-testid="delete-page-btn"]')
        assert delete_btn is not None
        await delete_btn.click()
        await asyncio.sleep(0.5)
        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        assert len(page_cards) == 4, f"Expected 4 page cards after deletion, found {len(page_cards)}"
        print("  [PASS] Page deleted. Total pages now 4.")

        # Step 8: Test Undo
        print("[Step 8] Testing Undo functionality...")
        undo_btn = await page.query_selector("#undo-btn")
        assert undo_btn is not None
        await undo_btn.click()
        await asyncio.sleep(0.5)
        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        assert len(page_cards) == 5, f"Expected 5 page cards after Undo, found {len(page_cards)}"
        print("  [PASS] Undo restored deleted page (count: 5).")

        # Step 9: Test Reset to original
        print("[Step 9] Testing Reset to original...")
        reset_btn = await page.query_selector("#reset-btn")
        assert reset_btn is not None
        await reset_btn.click()
        await asyncio.sleep(0.5)
        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        assert len(page_cards) == 4, f"Expected 4 page cards after Reset, found {len(page_cards)}"
        rot_badge = await page.query_selector("text=+90")
        assert rot_badge is None, "Expected rotation badge to be cleared after Reset"
        print("  [PASS] Reset restored original 4 pages with 0 deg rotation.")

        # Step 10: Apply edits for output generation:
        # Rotate page 1 (+90 deg), duplicate page 3, rotate duplicated copy (+180 deg), delete page 2
        print("[Step 10] Applying final edits: rotate P1 (+90), duplicate P3, rotate copy (+180), delete P2...")
        # 1. Rotate page 1
        p1_rot = await page_cards[0].query_selector('[data-testid="rotate-page-btn"]')
        await p1_rot.click()

        # 2. Duplicate page 3
        p3_dup = await page_cards[2].query_selector('[data-testid="duplicate-page-btn"]')
        await p3_dup.click()
        await asyncio.sleep(0.4)

        # 3. Rotate duplicated page (which is now index 3) twice to get +180 deg
        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        p3_copy_rot = await page_cards[3].query_selector('[data-testid="rotate-page-btn"]')
        await p3_copy_rot.click()
        await asyncio.sleep(0.2)
        await p3_copy_rot.click()

        # 4. Delete page 2 (index 1)
        p2_del = await page_cards[1].query_selector('[data-testid="delete-page-btn"]')
        await p2_del.click()
        await asyncio.sleep(0.4)

        page_cards = await page.query_selector_all('[data-testid="page-card"]')
        assert len(page_cards) == 4, f"Expected 4 pages in final order, found {len(page_cards)}"
        print("  [PASS] Edits configured. Output will contain 4 pages.")

        # Step 11: Set custom filename and submit
        print("[Step 11] Compiling and organizing PDF...")
        fname_input = await page.query_selector("#output-filename-input")
        if fname_input:
            await fname_input.fill("my_custom_organized.pdf")

        submit_btn = await page.query_selector("#organize-submit-btn")
        assert submit_btn is not None
        await submit_btn.click()

        # Wait for completion
        print("  Waiting for worker completion...")
        await page.wait_for_selector("#download-btn", timeout=25000)
        print("  [PASS] Organization finished! Download button displayed.")

        # Step 12: Verify Download and output PDF file
        print("[Step 12] Inspecting downloaded output PDF...")
        download_btn = await page.query_selector("#download-btn")
        assert download_btn is not None, "Download button not found!"

        # Download result via Playwright download handler
        async with page.expect_download() as download_info:
            await download_btn.click()
        download = await download_info.value
        download_path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
        await download.save_as(download_path)

        # Inspect downloaded PDF
        reader = pypdf.PdfReader(download_path)
        assert len(reader.pages) == 4, f"Expected 4 pages in downloaded PDF, got {len(reader.pages)}"

        # P0: original P1 (width 200, height 300, rotated +90)
        p0 = reader.pages[0]
        assert float(p0.mediabox.width) == 200.0
        assert float(p0.mediabox.height) == 300.0
        assert p0.rotation == 90

        # P1: original P3 (width 300, height 400, rot 0)
        p1 = reader.pages[1]
        assert float(p1.mediabox.width) == 300.0
        assert float(p1.mediabox.height) == 400.0
        assert p1.rotation == 0

        # P2: duplicated original P3 (width 300, height 400, rot 180)
        p2 = reader.pages[2]
        assert float(p2.mediabox.width) == 300.0
        assert float(p2.mediabox.height) == 400.0
        assert p2.rotation == 180

        # P3: original P4 (width 350, height 450, rot 0)
        p3 = reader.pages[3]
        assert float(p3.mediabox.width) == 350.0
        assert float(p3.mediabox.height) == 450.0
        assert p3.rotation == 0

        # Check metadata
        assert reader.metadata is not None
        assert reader.metadata.title == "Browser Verification Document"
        assert reader.metadata.author == "DocForge E2E"
        print("  [PASS] Downloaded PDF verified: 4 pages, correct dimensions, rotations, and metadata!")

        # Step 13: Regression Checks for all tools
        print("[Step 13] Checking tool route health regressions...")
        routes = [
            "/merge",
            "/split",
            "/compress",
            "/rotate",
            "/watermark",
            "/page-numbers",
            "/protect",
            "/unlock",
            "/extract-pages",
            "/organize-pdf",
        ]
        for route in routes:
            resp = await page.goto(f"http://localhost:3000{route}")
            assert resp.status == 200, f"Route {route} returned status {resp.status}"
            h1 = await page.text_content("h1")
            assert len(h1) > 0
            print(f"  [PASS] Route {route} healthy (200 OK, title: '{h1.strip()}')")

        await browser.close()
        print("=== BROWSER E2E VERIFICATION COMPLETED SUCCESSFULLY ===")

    # Cleanup temp files
    for p_path in [test_pdf_path, encrypted_pdf_path, dummy_txt_path]:
        try:
            if os.path.exists(p_path):
                os.remove(p_path)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_browser_verification())
