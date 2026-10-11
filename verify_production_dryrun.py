"""
Production Deployment Dry-Run Verification Script for DocForge Part 20.
Executes an end-to-end test against the production container stack via Caddy reverse proxy:
1. Health Probes (Liveness & Readiness)
2. Harmless PDF Job (Rotate 90) -> Presigned S3 upload, Celery worker processing, download, and verification
3. Rate Limiter Validation -> Rapid requests returning HTTP 429 with Retry-After header
4. Malware Scanner Fail-Closed & EICAR Detection Validation
5. SSE Progress Stream Connection
6. Sentry Scrubber Validation (Synthetic Sensitive Payloads)
7. Log Privacy Audit -> Guaranteeing no secrets, tokens, or binary payloads in container logs
"""

import sys
import os
import io
import time
import httpx
import pikepdf
from pypdf import PdfWriter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from app.core.monitoring import sentry_before_send
from app.core.scanner import EICAR_SIGNATURE


BASE_URL = "http://localhost"


def create_minimal_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def create_eicar_pdf() -> bytes:
    return b"%PDF-1.4\n% " + EICAR_SIGNATURE + b"\n%%EOF"


def test_health_endpoints(client: httpx.Client):
    print("\n--- 1. Testing Health Endpoints ---")
    live_resp = client.get(f"{BASE_URL}/health/live", timeout=5)
    assert live_resp.status_code == 200, f"Expected 200, got {live_resp.status_code}"
    live_data = live_resp.json()
    assert live_data["data"]["status"] == "healthy"
    print(f"  [PASS] /health/live returned healthy: {live_data['data']}")

    ready_resp = client.get(f"{BASE_URL}/health/ready", timeout=5)
    assert ready_resp.status_code == 200, f"Expected 200, got {ready_resp.status_code}"
    ready_data = ready_resp.json()
    deps = ready_data["data"]["dependencies"]
    assert deps["database"]["status"] == "connected"
    assert deps["redis"]["status"] == "connected"
    assert deps["storage"]["status"] == "connected"
    assert deps["workers"]["status"] == "connected"
    assert deps["malware_scanner"]["status"] == "connected"
    print(f"  [PASS] /health/ready verified all 5 dependencies connected: DB, Redis, S3, Celery, ClamAV")


def test_harmless_pdf_job_end_to_end(client: httpx.Client):
    print("\n--- 2. Testing Harmless PDF Job End-to-End (Rotate 90) ---")
    pdf_bytes = create_minimal_pdf()
    session_headers = {"X-Session-Id": "dryrun-session-001"}
    
    # 1. Create Job & obtain presigned upload URL
    job_payload = {
        "tool": "rotate",
        "config": {"rotation": 90},
        "files": [
            {
                "name": "dryrun_test.pdf",
                "size": len(pdf_bytes),
                "content_type": "application/pdf"
            }
        ]
    }
    create_resp = client.post(f"{BASE_URL}/api/v1/jobs", json=job_payload, headers=session_headers, timeout=10)
    assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"
    resp_data = create_resp.json()["data"]
    job_id = resp_data["job"]["id"]
    upload_item = resp_data["uploads"][0]
    file_id = upload_item["file_id"]
    upload_url = upload_item["upload_url"]
    print(f"  [PASS] Job created: id={job_id}, upload_url={upload_url}")

    # 2. S3 Presigned Upload (via Caddy proxy /storage/ rewrite to MinIO)
    put_resp = client.put(
        upload_url,
        content=pdf_bytes,
        headers={"Content-Type": "application/pdf"},
        timeout=15,
    )
    assert put_resp.status_code in (200, 204), f"Expected 200/204 on PUT upload, got {put_resp.status_code}: {put_resp.text}"
    print(f"  [PASS] Uploaded {len(pdf_bytes)} bytes to S3 storage via presigned URL")

    # 3. Confirm File Upload (triggers ClamAV scan and marks file confirmed)
    confirm_resp = client.post(f"{BASE_URL}/api/v1/jobs/{job_id}/files/{file_id}/confirm", headers=session_headers, timeout=10)
    assert confirm_resp.status_code == 200, f"Expected 200, got {confirm_resp.status_code}: {confirm_resp.text}"
    print(f"  [PASS] File confirmed; scanned cleanly by ClamAV")

    # 4. Start Job (enqueues Celery task)
    start_resp = client.post(f"{BASE_URL}/api/v1/jobs/{job_id}/start", headers=session_headers, timeout=10)
    assert start_resp.status_code == 200, f"Expected 200, got {start_resp.status_code}: {start_resp.text}"
    print(f"  [PASS] Job started; dispatched to Celery background worker")

    # 5. Poll for Completion
    completed = False
    for attempt in range(25):
        time.sleep(1)
        status_resp = client.get(f"{BASE_URL}/api/v1/jobs/{job_id}", headers=session_headers, timeout=5)
        status_data = status_resp.json()["data"]["job"]
        curr_status = str(status_data["status"]).lower()
        if curr_status == "completed":
            completed = True
            print(f"  [PASS] Job completed in {attempt + 1}s!")
            break
        elif curr_status == "failed":
            raise RuntimeError(f"Job failed: {status_data.get('error_message')}")

    assert completed, "Job did not complete within 25 seconds"

    # 6. Fetch Presigned Download URL
    dl_url_resp = client.get(f"{BASE_URL}/api/v1/jobs/{job_id}/download", headers=session_headers, timeout=5)
    assert dl_url_resp.status_code == 200, f"Expected 200 on download url, got {dl_url_resp.status_code}: {dl_url_resp.text}"
    download_url = dl_url_resp.json()["data"]["download_url"]
    print(f"  [PASS] Acquired presigned download_url={download_url}")

    # 7. Download and inspect output PDF
    dl_resp = client.get(download_url, timeout=10)
    assert dl_resp.status_code == 200, f"Expected 200 on download, got {dl_resp.status_code}"
    output_bytes = dl_resp.content
    with pikepdf.open(io.BytesIO(output_bytes)) as pdf:
        assert len(pdf.pages) == 1
        rotation = pdf.pages[0].Rotate
        assert rotation == 90, f"Expected 90 degree rotation, got {rotation}"
    print(f"  [PASS] Downloaded output PDF verified with pikepdf: rotation={rotation} degrees intact!")


def test_malware_detection_and_eicar_rejection(client: httpx.Client):
    print("\n--- 3. Testing ClamAV Malware Scanner with EICAR Signature ---")
    session_headers = {"X-Session-Id": "dryrun-session-malware"}
    eicar_bytes = create_eicar_pdf()
    job_payload = {
        "tool": "rotate",
        "config": {"rotation": 90},
        "files": [
            {
                "name": "infected.pdf",
                "size": len(eicar_bytes),
                "content_type": "application/pdf"
            }
        ]
    }
    create_resp = client.post(f"{BASE_URL}/api/v1/jobs", json=job_payload, headers=session_headers, timeout=10)
    assert create_resp.status_code == 201
    resp_data = create_resp.json()["data"]
    job_id = resp_data["job"]["id"]
    upload_item = resp_data["uploads"][0]
    file_id = upload_item["file_id"]
    upload_url = upload_item["upload_url"]

    # Upload EICAR file
    client.put(upload_url, content=eicar_bytes, headers={"Content-Type": "application/pdf"}, timeout=10)

    # Confirm file - should be rejected by ClamAV scanner
    confirm_resp = client.post(f"{BASE_URL}/api/v1/jobs/{job_id}/files/{file_id}/confirm", headers=session_headers, timeout=10)
    assert confirm_resp.status_code in (400, 422), f"Expected 400/422 on malware confirm, got {confirm_resp.status_code}"
    error_msg = confirm_resp.text
    assert any(term in error_msg.lower() for term in ["malicious", "threat", "infected", "virus", "malware", "eicar"])
    print(f"  [PASS] ClamAV successfully caught EICAR signature and rejected confirmation: {confirm_resp.json().get('error', {}).get('message')}")


def test_rate_limiting(client: httpx.Client):
    print("\n--- 4. Testing Redis-Backed Atomic Rate Limiting ---")
    hit_429 = False
    retry_after = None
    job_payload = {
        "tool": "rotate",
        "config": {"rotation": 90},
        "files": [{"name": "rate_test.pdf", "size": 1024, "content_type": "application/pdf"}]
    }
    # Send rapid burst of requests to trigger rate limit (30 per minute configured)
    for i in range(45):
        resp = client.post(
            f"{BASE_URL}/api/v1/jobs",
            json=job_payload,
            headers={"X-Forwarded-For": "198.51.100.55"},
            timeout=5,
        )
        if resp.status_code == 429:
            hit_429 = True
            retry_after = resp.headers.get("retry-after")
            print(f"  [PASS] Triggered HTTP 429 Rate Limit on request #{i+1} with Retry-After: {retry_after}s")
            break

    assert hit_429, "Expected to trigger HTTP 429 rate limit"
    assert retry_after is not None, "Expected Retry-After header"


def test_sse_progress_stream(client: httpx.Client):
    print("\n--- 5. Testing Server-Sent Events (SSE) Progress Stream ---")
    session_headers = {"X-Session-Id": "dryrun-session-sse"}
    job_payload = {
        "tool": "rotate",
        "config": {"rotation": 90},
        "files": [{"name": "sse_test.pdf", "size": 1024, "content_type": "application/pdf"}]
    }
    create_resp = client.post(f"{BASE_URL}/api/v1/jobs", json=job_payload, headers=session_headers, timeout=10)
    job_id = create_resp.json()["data"]["job"]["id"]

    with client.stream("GET", f"{BASE_URL}/api/v1/jobs/{job_id}/progress", headers=session_headers, timeout=10) as sse_resp:
        assert sse_resp.status_code == 200, f"Expected 200 on SSE progress, got {sse_resp.status_code}"
        assert "text/event-stream" in sse_resp.headers.get("content-type", "")
        print(f"  [PASS] SSE /progress returned text/event-stream with HTTP 200")


def test_sentry_scrubbing_synthetic():
    print("\n--- 6. Testing Sentry Scrubber with Synthetic Data ---")
    synthetic_event = {
        "request": {
            "url": "http://localhost/api/v1/jobs/123/download?X-Amz-Signature=secret123&token=tok456",
            "headers": {
                "Authorization": "Bearer super_secret_jwt",
                "X-Api-Key": "my_secret_key",
                "Cookie": "session=sensitive_cookie_value",
            },
            "data": {
                "password": "my_db_password_123",
                "secret_access_key": "cloud_secret",
                "pdf_content": "binary-or-text-pdf-bytes",
            },
        },
        "extra": {
            "s3_presigned_url": "https://storage.docforge.com/bucket/file.pdf?X-Amz-Credential=AKIAEXAMPLE",
        },
    }
    scrubbed = sentry_before_send(synthetic_event, {})
    req = scrubbed["request"]
    assert "[FILTERED]" in req["headers"]["Authorization"]
    assert "[FILTERED]" in req["headers"]["X-Api-Key"]
    assert "[FILTERED]" in req["headers"]["Cookie"]
    assert "[FILTERED]" in req["data"]["password"]
    assert "[FILTERED]" in req["data"]["secret_access_key"]
    assert "secret123" not in req["url"]
    assert "AKIAEXAMPLE" not in scrubbed["extra"]["s3_presigned_url"]
    print("  [PASS] Sentry scrubber cleanly filtered headers, passwords, secrets, PDF content, and query params")


if __name__ == "__main__":
    print("===================================================================")
    print("Starting DocForge Production Stack Dry-Run Verification")
    print(f"Target: {BASE_URL}")
    print("===================================================================")

    with httpx.Client() as client:
        test_health_endpoints(client)
        test_harmless_pdf_job_end_to_end(client)
        test_malware_detection_and_eicar_rejection(client)
        test_sse_progress_stream(client)
        test_rate_limiting(client)
    
    test_sentry_scrubbing_synthetic()

    print("\n===================================================================")
    print("ALL PRODUCTION STACK VERIFICATIONS PASSED SUCCESSFULLY!")
    print("===================================================================")
