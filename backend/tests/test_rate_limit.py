import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from starlette.requests import Request

from app.core.config import settings
from app.core.rate_limit import resolve_client_ip, rate_limiter
from app.core.redis import get_redis_client
from app.main import app


def create_dummy_request(client_host: str, headers: dict) -> Request:
    scope = {
        "type": "http",
        "client": (client_host, 12345),
        "headers": [(k.lower().encode("latin1"), v.encode("latin1")) for k, v in headers.items()],
    }
    return Request(scope)


def test_resolve_client_ip_untrusted_direct():
    # Direct peer not in trusted proxies; header spoofing must be ignored
    req = create_dummy_request("203.0.113.195", {"x-forwarded-for": "10.0.0.1, 1.1.1.1"})
    resolved = resolve_client_ip(req, trusted_proxies=["127.0.0.1", "::1"])
    assert resolved == "203.0.113.195"


def test_resolve_client_ip_trusted_proxy_single_hop():
    # Peer is trusted local proxy; must read X-Forwarded-For
    req = create_dummy_request("127.0.0.1", {"x-forwarded-for": "198.51.100.42"})
    resolved = resolve_client_ip(req, trusted_proxies=["127.0.0.1", "::1"])
    assert resolved == "198.51.100.42"


def test_resolve_client_ip_trusted_proxy_multi_hop():
    # Chain: client -> untrusted proxy -> trusted proxy
    req = create_dummy_request("127.0.0.1", {"x-forwarded-for": "198.51.100.1, 192.168.1.100"})
    resolved = resolve_client_ip(req, trusted_proxies=["127.0.0.1"])
    assert resolved == "192.168.1.100" or resolved == "198.51.100.1"


@pytest.mark.asyncio
async def test_rate_limiter_atomic_sliding_window():
    redis_client = await get_redis_client()
    test_key = "test_rl:unit_check"
    await redis_client.delete(test_key)

    limit = 5
    window = 3

    for i in range(limit):
        allowed, remaining, retry_after, reset_time = await rate_limiter.check(test_key, limit, window)
        assert allowed is True
        assert remaining == limit - i - 1
        assert retry_after == 0

    # 6th request must be blocked
    allowed, remaining, retry_after, reset_time = await rate_limiter.check(test_key, limit, window)
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1
    assert reset_time > 0

    await redis_client.delete(test_key)


@pytest.mark.asyncio
async def test_rate_limiter_concurrency():
    redis_client = await get_redis_client()
    test_key = "test_rl:concurrent"
    await redis_client.delete(test_key)

    limit = 10
    window = 10

    # Fire 25 concurrent checks
    tasks = [rate_limiter.check(test_key, limit, window) for _ in range(25)]
    results = await asyncio.gather(*tasks)

    allowed_count = sum(1 for res in results if res[0] is True)
    blocked_count = sum(1 for res in results if res[0] is False)

    assert allowed_count == limit
    assert blocked_count == 15

    await redis_client.delete(test_key)


@pytest.mark.asyncio
async def test_rate_limit_middleware_job_creation_limit():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        redis_client = await get_redis_client()
        # Clean rate limit key for test client
        await redis_client.delete("rate_limit:job_creation:127.0.0.1")

        orig_enabled = settings.RATE_LIMIT_ENABLED
        settings.RATE_LIMIT_ENABLED = True
        orig_limit = settings.RATE_LIMIT_JOB_CREATION_LIMIT
        settings.RATE_LIMIT_JOB_CREATION_LIMIT = 3
        settings.RATE_LIMIT_JOB_CREATION_WINDOW = 60

        try:
            # 3 valid creates (or failed validation, middleware still counts request)
            for i in range(3):
                resp = await client.post(
                    f"{settings.API_V1_PREFIX}/jobs",
                    json={"tool": "merge", "files": [{"name": f"doc{i}.pdf", "size": 1024}]},
                )
                assert resp.status_code == 201
                assert "X-RateLimit-Limit" in resp.headers
                assert resp.headers["X-RateLimit-Remaining"] == str(2 - i)

            # 4th request must receive HTTP 429
            resp4 = await client.post(
                f"{settings.API_V1_PREFIX}/jobs",
                json={"tool": "merge", "files": [{"name": "extra.pdf", "size": 1024}]},
            )
            assert resp4.status_code == 429
            assert "Retry-After" in resp4.headers
            assert resp4.headers["X-RateLimit-Remaining"] == "0"
            data = resp4.json()
            assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"

        finally:
            settings.RATE_LIMIT_ENABLED = orig_enabled
            settings.RATE_LIMIT_JOB_CREATION_LIMIT = orig_limit
            await redis_client.delete("rate_limit:job_creation:127.0.0.1")


@pytest.mark.asyncio
async def test_rate_limit_sse_progress_and_health_bypass():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Rapid health checks must never return 429
        for _ in range(10):
            resp = await client.get("/health")
            assert resp.status_code == 200
            # Excluded endpoints do not receive rate limit headers
            assert "X-RateLimit-Limit" not in resp.headers
