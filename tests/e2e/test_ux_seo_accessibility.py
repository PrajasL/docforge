import os
import sys
import json
import xml.etree.ElementTree as ET
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"

ALL_17_ROUTES = [
    "/",
    "/tools",
    "/privacy",
    "/terms",
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
    "/pdf-to-jpg",
    "/jpg-to-pdf",
    "/repair-pdf",
]

def run_ux_seo_accessibility_tests():
    results = {}
    print("=== Starting E2E Tests for UX, SEO & Accessibility ===")

    with open("frontend/node_modules/axe-core/axe.min.js", "r", encoding="utf-8") as f:
        axe_script = f.read()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Theme Persistence
        print("\n[1/6] Testing theme persistence...")
        page.goto(f"{BASE_URL}/tools", wait_until="networkidle")
        initial_dark = page.evaluate("() => document.documentElement.classList.contains('dark')")
        theme_toggle = page.locator("#theme-toggle-btn").first
        theme_toggle.wait_for(timeout=5000)
        theme_toggle.click()
        page.wait_for_timeout(300)
        toggled_dark = page.evaluate("() => document.documentElement.classList.contains('dark')")
        assert toggled_dark != initial_dark, "Theme class did not toggle"
        stored_theme = page.evaluate("() => localStorage.getItem('docforge_theme')")
        assert stored_theme in ["dark", "light"], f"Invalid stored theme: {stored_theme}"

        # Navigate to another page and verify theme remains persisted
        page.goto(f"{BASE_URL}/merge", wait_until="networkidle")
        persisted_dark = page.evaluate("() => document.documentElement.classList.contains('dark')")
        assert persisted_dark == toggled_dark, "Theme was not persisted across navigation"
        results["theme_persistence"] = f"PASSED (Theme toggled and persisted: stored='{stored_theme}')"
        print(f" -> {results['theme_persistence']}")

        # 2. Shared Headers & Navigation
        print("\n[2/6] Testing navigation and shared headers...")
        page.goto(f"{BASE_URL}/tools", wait_until="networkidle")
        # Click brand link to return home
        brand_link = page.locator("a:has-text('DocForge')").first
        brand_link.click()
        page.wait_for_url(f"{BASE_URL}/", timeout=5000)
        assert page.url.rstrip("/") == BASE_URL

        # Click legal links in footer
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.locator("footer a:has-text('Privacy')").first.click()
        page.wait_for_url("**/privacy", timeout=5000)
        assert page.locator("h1:has-text('Privacy Policy')").is_visible()

        page.locator("footer a:has-text('Terms')").first.click()
        page.wait_for_url("**/terms", timeout=5000)
        assert page.locator("h1:has-text('Terms of Service')").is_visible()
        results["navigation"] = "PASSED (Header and footer navigation verified)"
        print(f" -> {results['navigation']}")

        # 3. Responsive Layout (Mobile 375x667)
        print("\n[3/6] Testing responsive layout on mobile viewport (375x667)...")
        page.set_viewport_size({"width": 375, "height": 667})
        for path in ["/", "/tools", "/merge", "/privacy", "/terms"]:
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            has_overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
            assert not has_overflow, f"Horizontal overflow detected on mobile viewport for {path}"
        # Reset viewport
        page.set_viewport_size({"width": 1280, "height": 800})
        results["responsive_layout"] = "PASSED (No horizontal overflow on 375px mobile viewport)"
        print(f" -> {results['responsive_layout']}")

        # 4. Robots.txt and Sitemap.xml
        print("\n[4/6] Testing robots.txt and sitemap.xml...")
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # robots.txt
            robots_resp = client.get("/robots.txt")
            assert robots_resp.status_code == 200, f"robots.txt status: {robots_resp.status_code}"
            assert "user-agent:" in robots_resp.text.lower()
            assert "sitemap:" in robots_resp.text.lower()
            assert "sitemap.xml" in robots_resp.text

            # sitemap.xml
            sitemap_resp = client.get("/sitemap.xml")
            assert sitemap_resp.status_code == 200, f"sitemap.xml status: {sitemap_resp.status_code}"
            root = ET.fromstring(sitemap_resp.content)
            # namespace handling
            urls = [loc.text for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
            print(f"    Sitemap contains {len(urls)} URLs")
            assert len(urls) == 17, f"Expected 17 URLs in sitemap, got {len(urls)}: {urls}"
            assert any(u.endswith("/privacy") for u in urls), "Privacy missing from sitemap"
            assert any(u.endswith("/terms") for u in urls), "Terms missing from sitemap"
            assert any(u.endswith("/repair-pdf") for u in urls), "Repair PDF missing from sitemap"
            results["sitemap_robots"] = f"PASSED (robots.txt and sitemap.xml verified with all {len(urls)} canonical URLs)"
            print(f" -> {results['sitemap_robots']}")

        # 5. Canonical URLs
        print("\n[5/6] Testing canonical link tags...")
        for path in ["/", "/tools", "/privacy", "/terms", "/merge", "/rotate", "/repair-pdf"]:
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            canonical_href = page.locator("link[rel='canonical']").get_attribute("href")
            assert canonical_href is not None and len(canonical_href) > 0, f"Canonical tag missing on {path}"
            assert canonical_href.endswith(path) or (path == "/" and not canonical_href.endswith("//"))
        results["canonical_urls"] = "PASSED (Canonical tags verified on all tested pages)"
        print(f" -> {results['canonical_urls']}")

        # 6. Automated WCAG 2.1 AA axe-core Audit
        print("\n[6/6] Running automated WCAG 2.1 AA axe-core audit across all 17 routes...")
        violations_summary = {}
        for path in ALL_17_ROUTES:
            page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
            page.evaluate(axe_script)
            scan_res = page.evaluate("axe.run({ runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } })")
            v_list = scan_res.get("violations", [])
            violations_summary[path] = len(v_list)
            assert len(v_list) == 0, f"Accessibility violations found on {path}: {v_list}"
            print(f"    {path}: 0 violations")

        results["accessibility_axe"] = f"PASSED (All 17 routes have 0 WCAG 2.1 AA violations)"
        print(f" -> {results['accessibility_axe']}")

        browser.close()

    print("\n=== SUMMARY OF UX, SEO & ACCESSIBILITY ===")
    for test, res in results.items():
        print(f"  [{test.upper()}]: {res}")
    assert len(results) == 6, f"Expected 6 test categories, got {len(results)}"
    return results

if __name__ == "__main__":
    run_ux_seo_accessibility_tests()
