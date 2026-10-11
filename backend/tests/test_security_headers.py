import pytest
from httpx import AsyncClient, ASGITransport
from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_security_headers_present_on_api_responses():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200

        # Verify MIME protection
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

        # Verify Clickjacking protection
        assert resp.headers["X-Frame-Options"] == "DENY"

        # Verify Referrer policy
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

        # Verify Content-Security-Policy
        assert "Content-Security-Policy" in resp.headers
        csp = resp.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

        # Verify Permissions-Policy
        assert "Permissions-Policy" in resp.headers
        assert "camera=()" in resp.headers["Permissions-Policy"]


@pytest.mark.asyncio
async def test_hsts_header_toggle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default dev mode: HSTS is disabled
        settings.ENABLE_HSTS = False
        settings.ENVIRONMENT = "development"
        resp_dev = await client.get("/health")
        assert "Strict-Transport-Security" not in resp_dev.headers

        # Production / enabled mode: HSTS must be present
        settings.ENABLE_HSTS = True
        try:
            resp_prod = await client.get("/health")
            assert "Strict-Transport-Security" in resp_prod.headers
            assert "max-age=31536000" in resp_prod.headers["Strict-Transport-Security"]
        finally:
            settings.ENABLE_HSTS = False
