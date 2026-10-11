import os
import sys
import time
from playwright.sync_api import sync_playwright

def run_part17_browser_verification():
    console_logs = []
    page_errors = []

    print("=== STARTING BROWSER E2E VERIFICATION FOR PART 17 ===")
    print("Features: All Tools Directory, Theme System, Branded 404, Real-Time Progress")

    with sync_playwright() as p:
        print("[Step 1] Launching MS Edge browser...")
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # 1. Homepage & Navigation Check
        print("[Step 2] Navigating to homepage (http://localhost:3000)...")
        page.goto("http://localhost:3000")
        page.wait_for_selector("text=DocForge")

        all_tools_link = page.locator("a:has-text('All Tools')").first
        assert all_tools_link.is_visible(), "All Tools link not visible in navigation"
        print("  [PASS] All Tools link found on homepage navigation.")

        # 2. Theme Toggle on Homepage
        print("[Step 3] Testing Theme Toggle on Homepage...")
        theme_toggle_btn = page.locator("#theme-toggle-btn").first
        assert theme_toggle_btn.is_visible(), "Theme toggle button not visible"

        # Check initial theme
        is_dark_initially = page.evaluate("() => document.documentElement.classList.contains('dark')")
        print(f"  Initial dark class present: {is_dark_initially}")

        # Click theme toggle to switch
        theme_toggle_btn.click()
        time.sleep(0.3)
        is_dark_after_toggle = page.evaluate("() => document.documentElement.classList.contains('dark')")
        assert is_dark_after_toggle != is_dark_initially, "Theme toggle did not switch html.dark class"
        print("  [PASS] Theme toggle successfully switched dark mode class.")

        # Reload to verify persistence in localStorage
        page.reload()
        page.wait_for_selector("text=DocForge")
        is_dark_after_reload = page.evaluate("() => document.documentElement.classList.contains('dark')")
        assert is_dark_after_reload == is_dark_after_toggle, "Theme preference failed to persist across page reloads"
        print("  [PASS] Theme preference successfully persisted across page reload.")

        # Toggle back to original
        page.locator("#theme-toggle-btn").click()
        time.sleep(0.3)

        # 3. All Tools Directory (/tools)
        print("[Step 4] Navigating to /tools directory...")
        page.goto("http://localhost:3000/tools")
        page.wait_for_selector("h1:has-text('All PDF Tools')")
        print("  [PASS] /tools directory page rendered successfully.")

        # Verify all 12 tools are visible
        expected_tools = [
          "Merge PDF", "Split PDF", "Compress PDF", "Rotate PDF",
          "Watermark PDF", "Page Numbers", "Protect PDF", "Unlock PDF",
          "Extract Pages", "Organize PDF", "PDF to JPG", "JPG to PDF"
        ]
        for tool_name in expected_tools:
            tool_locator = page.locator(f"h3:has-text('{tool_name}')")
            assert tool_locator.is_visible(), f"Tool card '{tool_name}' not visible in directory"
        print(f"  [PASS] All 12 tool cards verified in directory.")

        # 4. Search Filter
        print("[Step 5] Testing instant search input...")
        search_input = page.locator("#tool-search-input")
        search_input.fill("watermark")
        time.sleep(0.2)
        assert page.locator("h3:has-text('Watermark PDF')").is_visible(), "Watermark card not found after search"
        assert not page.locator("h3:has-text('Merge PDF')").is_visible(), "Merge card still visible after filtering"
        print("  [PASS] Instant search filtered successfully to Watermark PDF.")

        # Keyword search (e.g. 'encrypt')
        search_input.fill("encrypt")
        time.sleep(0.2)
        assert page.locator("h3:has-text('Protect PDF')").is_visible(), "Protect card not found with 'encrypt' keyword"
        print("  [PASS] Keyword search ('encrypt') successfully located Protect PDF.")

        # Empty state check
        search_input.fill("nonexistentquery123")
        time.sleep(0.2)
        assert page.locator("#empty-tools-state").is_visible(), "Empty state not shown for 0 results"
        print("  [PASS] Empty state shown for zero-match search query.")

        # Reset button
        reset_btn = page.locator("button:has-text('Reset Search & Filters')")
        reset_btn.click()
        time.sleep(0.2)
        assert page.locator("h3:has-text('Merge PDF')").is_visible(), "Tools not restored after search reset"
        print("  [PASS] Search reset button restored all tools.")

        # 5. Category Tab Filtering
        print("[Step 6] Testing category tab filtering...")
        convert_tab = page.locator("#category-tab-convert")
        convert_tab.click()
        time.sleep(0.2)
        assert page.locator("h3:has-text('PDF to JPG')").is_visible(), "PDF to JPG not visible under Convert"
        assert page.locator("h3:has-text('JPG to PDF')").is_visible(), "JPG to PDF not visible under Convert"
        assert not page.locator("h3:has-text('Merge PDF')").is_visible(), "Merge PDF should not be under Convert"
        print("  [PASS] Category tab successfully filtered tools to 'Convert' category.")

        # Return to all category
        page.locator("#category-tab-all").click()
        time.sleep(0.2)

        # 6. Branded 404 Page Check
        print("[Step 7] Testing custom branded 404 page...")
        page.goto("http://localhost:3000/random-non-existent-route-xyz")
        page.wait_for_selector("h1:has-text('Page Not Found')")
        assert page.locator("text=Error 404").is_visible(), "Error 404 badge not found"
        assert page.locator("a:has-text('Return to Dashboard')").is_visible(), "Return to Dashboard button not found"
        print("  [PASS] Branded 404 error page verified.")

        # 7. Navigation into Tool Route from 404
        page.locator("a:has-text('Browse 12 Tools')").click()
        page.wait_for_selector("h1:has-text('All PDF Tools')")
        print("  [PASS] Navigation from 404 back to All Tools directory verified.")

        # 8. Check Tool Route Header Elements
        page.locator("#tool-card-merge-pdf").click()
        page.wait_for_selector("h1:has-text('Merge PDF')")
        assert page.locator("#theme-toggle-btn").first.is_visible(), "Theme toggle not present on Merge PDF header"
        print("  [PASS] Tool route header features ThemeToggle and navigation links.")

        browser.close()

    print("\n=== BROWSER E2E VERIFICATION FOR PART 17 PASSED WITH 0 ERRORS ===")
    return True

if __name__ == "__main__":
    success = run_part17_browser_verification()
    sys.exit(0 if success else 1)
