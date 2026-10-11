import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "DocForge"
    assert "request_id" in data["meta"]
    assert response.headers.get("X-Request-ID") is not None
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.asyncio
async def test_health_check_liveness(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["version"] == "0.1.0"
    assert "request_id" in data["meta"]


@pytest.mark.asyncio
async def test_api_v1_health_check_liveness(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_readiness(async_client: AsyncClient):
    # When downstream services are not running, readiness returns 503 with degraded status
    response = await async_client.get("/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "services" in data["data"]
    assert "database" in data["data"]["services"]
    assert "redis" in data["data"]["services"]
    assert "storage" in data["data"]["services"]
