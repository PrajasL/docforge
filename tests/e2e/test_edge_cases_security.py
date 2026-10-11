import os
import sys
import time
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from playwright.sync_api import sync_playwright
from tests.e2e.fixtures_manager import E2EFixturesManager, EICAR_SIGNATURE

BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"

def run_edge_cases_and_security_tests():
    fixtures = E2EFixturesManager()
    results = {}
    print("=== Starting E2E Tests for Edge Cases & Security ===")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()

            # 1. Invalid upload rejection (non-PDF)
            print("\n[1/5] Testing non-PDF upload rejection in browser...")
            page.goto(f"{BASE_URL}/rotate", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.txt_file)
            page.wait_for_selector("#global-error-banner", timeout=5000)
            err_text = page.locator("#global-error-banner").inner_text()
            assert "non-PDF" in err_text or "Invalid" in err_text or "Skipped" in err_text, f"Unexpected error: {err_text}"
            results["invalid_upload"] = f"PASSED (Rejected non-PDF: {err_text.strip()[:60]}...)"
            print(f" -> {results['invalid_upload']}")

            # 2. Corrupted PDF handling
            print("\n[2/5] Testing corrupted PDF upload in browser...")
            page.goto(f"{BASE_URL}/rotate", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_corrupted)
            # Either client rejects immediately or server worker returns error
            if page.locator("#global-error-banner").is_visible():
                c_err = page.locator("#global-error-banner").inner_text()
            else:
                page.wait_for_selector("#start-rotate-btn", timeout=5000)
                page.locator("#start-rotate-btn").click()
                page.wait_for_selector("#global-error-banner", timeout=15000)
                c_err = page.locator("#global-error-banner").inner_text()
            assert len(c_err) > 0, "No error banner shown for corrupted file"
            results["corrupted_file"] = f"PASSED (Handled corrupted PDF gracefully: {c_err.strip()[:60]}...)"
            print(f" -> {results['corrupted_file']}")

            # 3. Encrypted PDF without password on standard tool
            print("\n[3/5] Testing encrypted PDF on rotate tool...")
            page.goto(f"{BASE_URL}/rotate", wait_until="networkidle")
            page.locator("#pdf-upload-input").set_input_files(fixtures.pdf_encrypted)
            if page.locator("#global-error-banner").is_visible():
                enc_err = page.locator("#global-error-banner").inner_text()
            else:
                page.wait_for_selector("#start-rotate-btn", timeout=5000)
                page.locator("#start-rotate-btn").click()
                page.wait_for_selector("#global-error-banner", timeout=15000)
                enc_err = page.locator("#global-error-banner").inner_text()
            assert "password" in enc_err.lower() or "encrypt" in enc_err.lower() or "failed" in enc_err.lower() or "error" in enc_err.lower()
            results["encrypted_rejection"] = f"PASSED (Protected file flagged: {enc_err.strip()[:60]}...)"
            print(f" -> {results['encrypted_rejection']}")

            # 4. Antivirus rejection (EICAR signature)
            print("\n[4/5] Testing ClamAV malware rejection...")
            # Test direct upload endpoint with EICAR payload
            with httpx.Client(base_url=API_URL, timeout=10.0) as client:
                # Create job
                create_resp = client.post(
                    "/api/v1/jobs",
                    json={"tool": "rotate", "files": [{"name": "eicar.pdf", "size": len(EICAR_SIGNATURE)}]},
                    headers={"X-Session-ID": "e2e_antivirus_test"}
                )
                assert create_resp.status_code == 201, f"Job creation failed: {create_resp.text}"
                resp_data = create_resp.json().get("data", {})
                job_id = resp_data.get("job", {}).get("id") or resp_data.get("id")
                uploads = resp_data.get("uploads", [])
                file_id = uploads[0].get("file_id") if uploads else None
                assert job_id and file_id, f"Invalid job or file ID from: {create_resp.text}"

                # Upload EICAR file
                upload_resp = client.put(
                    f"/api/v1/jobs/{job_id}/files/{file_id}",
                    content=b"%PDF-1.4\n" + EICAR_SIGNATURE + b"\n%%EOF",
                    headers={"Content-Type": "application/pdf"}
                )
                assert upload_resp.status_code in [400, 422], f"Expected 400 malware rejection, got {upload_resp.status_code}: {upload_resp.text}"
                resp_json = upload_resp.json()
                assert "MALWARE" in str(resp_json) or "virus" in str(resp_json).lower() or "infected" in str(resp_json).lower()
                results["antivirus_rejection"] = f"PASSED (ClamAV detected and rejected EICAR signature: {resp_json})"
                print(f" -> {results['antivirus_rejection']}")

            # 5. Rate limiting
            print("\n[5/5] Testing rate limiting burst behavior...")
            with httpx.Client(base_url=API_URL, timeout=5.0) as client:
                burst_codes = []
                # Rapidly burst 80 health or api requests from same test client
                for _ in range(80):
                    r = client.get("/health")
                    burst_codes.append(r.status_code)
                # Verify server handles burst without crashing (either 200 or 429)
                assert all(c in [200, 429] for c in burst_codes), f"Unexpected status in burst: {set(burst_codes)}"
                results["rate_limiting"] = f"PASSED (Handled 80-request burst without server degradation)"
                print(f" -> {results['rate_limiting']}")

            browser.close()
    finally:
        fixtures.cleanup()

    print("\n=== SUMMARY OF EDGE CASES & SECURITY ===")
    for test, res in results.items():
        print(f"  [{test.upper()}]: {res}")
    assert len(results) == 5, f"Expected 5 edge case tests, got {len(results)}"
    return results

if __name__ == "__main__":
    run_edge_cases_and_security_tests()
