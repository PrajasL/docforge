import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from botocore.exceptions import ClientError

from app.core.monitoring import (
    sanitize_url,
    sanitize_data_dict,
    sentry_before_send,
    sentry_before_breadcrumb,
    init_monitoring,
)
from app.core.storage import S3StorageBackend
from app.core.scanner import ClamAVScanner


# ===================================================================
# 1. Monitoring & Telemetry Data Scrubber Tests
# ===================================================================

def test_sanitize_url_removes_sensitive_parameters():
    url = "https://bucket.r2.cloudflarestorage.com/docforge-inputs/file.pdf?X-Amz-Signature=secret123&X-Amz-Credential=cred456&safe_param=hello"
    sanitized = sanitize_url(url)
    assert "secret123" not in sanitized
    assert "cred456" not in sanitized
    assert "%5BFILTERED%5D" in sanitized or "[FILTERED]" in sanitized
    assert "safe_param=hello" in sanitized


def test_sanitize_data_dict_recursively_filters_secrets():
    payload = {
        "user_email": "user@example.com",
        "password": "SuperSecretPassword123!",
        "api_key": "sk-12345678",
        "nested": {
            "token": "bearer-token-val",
            "normal_field": "visible",
            "pdf_data": b"%PDF-1.4 binary content...",
        },
    }
    cleaned = sanitize_data_dict(payload)
    assert cleaned["user_email"] == "user@example.com"
    assert cleaned["password"] == "[FILTERED]"
    assert cleaned["api_key"] == "[FILTERED]"
    assert cleaned["nested"]["token"] == "[FILTERED]"
    assert cleaned["nested"]["normal_field"] == "visible"
    assert "[FILTERED_BINARY" in cleaned["nested"]["pdf_data"]


def test_sentry_before_send_scrubs_headers_and_upload_payloads():
    event = {
        "request": {
            "url": "https://api.docforge.com/api/v1/jobs?token=secrettoken",
            "headers": {
                "Authorization": "Bearer supersecretjwt",
                "Cookie": "session_id=12345",
                "Content-Type": "multipart/form-data; boundary=something",
                "User-Agent": "Mozilla/5.0",
            },
            "data": "raw binary multipart upload with pdf content inside",
        },
        "breadcrumbs": {
            "values": [
                {
                    "data": {
                        "url": "https://s3.amazonaws.com/test.pdf?X-Amz-Signature=sig789",
                        "password": "pass",
                    }
                }
            ]
        },
    }

    filtered = sentry_before_send(event, {})
    assert filtered is not None

    # Headers sanitized
    headers = filtered["request"]["headers"]
    assert headers["Authorization"] == "[FILTERED]"
    assert headers["Cookie"] == "[FILTERED]"
    assert headers["User-Agent"] == "Mozilla/5.0"

    # URL query sanitized
    assert "secrettoken" not in filtered["request"]["url"]
    assert "%5BFILTERED%5D" in filtered["request"]["url"] or "[FILTERED]" in filtered["request"]["url"]

    # Multipart body replaced
    assert filtered["request"]["data"] == "[FILTERED_UPLOAD_PAYLOAD]"

    # Breadcrumb sanitized
    bc = filtered["breadcrumbs"]["values"][0]["data"]
    assert "sig789" not in bc["url"]
    assert bc["password"] == "[FILTERED]"


def test_init_monitoring_disabled_without_dsn():
    with patch("app.core.config.settings.SENTRY_DSN", ""):
        # Should not raise or initialize sentry
        init_monitoring()


# ===================================================================
# 2. Production Storage & Presigned URL Override Tests
# ===================================================================

def test_presigned_url_override():
    backend = S3StorageBackend(
        endpoint_url="http://minio:9000",
        presigned_endpoint_override="https://storage.docforge.example.com",
    )
    raw_url = "http://minio:9000/docforge-inputs/doc.pdf?X-Amz-Expires=900"
    overridden = backend._apply_presigned_url_override(raw_url)
    assert overridden.startswith("https://storage.docforge.example.com/docforge-inputs/doc.pdf")


@pytest.mark.asyncio
async def test_storage_check_health_scoped_token_fallback():
    """Verify that 403 / AccessDenied on list_buckets falls back to head_bucket."""
    backend = S3StorageBackend(
        provider="r2",
        inputs_bucket="docforge-inputs",
        outputs_bucket="docforge-outputs",
    )

    mock_client = AsyncMock()
    # list_buckets raises AccessDenied (standard for Cloudflare R2 scoped tokens)
    mock_client.list_buckets.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "ListBuckets",
    )
    mock_client.head_bucket.return_value = {}

    with patch.object(backend, "_get_client_context") as mock_ctx:
        mock_ctx.return_value.__aenter__.return_value = mock_client
        mock_ctx.return_value.__aexit__.return_value = None

        result = await backend.check_health()
        assert result["status"] == "connected"
        assert result["provider"] == "r2"
        assert result.get("scoped_token") is True
        mock_client.head_bucket.assert_awaited_once_with(Bucket="docforge-inputs")


# ===================================================================
# 3. Health & Observability Endpoints Tests
# ===================================================================

@pytest.mark.asyncio
async def test_health_live_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["service"] == "DocForge"


@pytest.mark.asyncio
async def test_health_ready_endpoint_structure(async_client: AsyncClient):
    response = await async_client.get("/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "data" in data
    assert "application" in data["data"]
    assert data["data"]["application"]["status"] == "healthy"
    assert "dependencies" in data["data"]

    deps = data["data"]["dependencies"]
    assert "database" in deps
    assert "redis" in deps
    assert "storage" in deps
    assert "workers" in deps
    assert "malware_scanner" in deps


@pytest.mark.asyncio
async def test_clamav_scanner_check_health_disabled():
    scanner = ClamAVScanner(enabled=False)
    result = await scanner.check_health()
    assert result["status"] == "disabled"
    assert result["enabled"] is False


@pytest.mark.asyncio
async def test_clamav_scanner_check_health_connected():
    scanner = ClamAVScanner(enabled=True)
    with patch.object(scanner, "ping", AsyncMock(return_value=True)):
        result = await scanner.check_health()
        assert result["status"] == "connected"
        assert result["enabled"] is True
