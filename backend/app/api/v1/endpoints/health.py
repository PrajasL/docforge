import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_database_health
from app.core.errors import get_request_id
from app.core.logging import logger
from app.core.redis import check_redis_health
from app.core.scanner import check_scanner_health
from app.core.storage import check_storage_health

router = APIRouter(tags=["health"])


async def check_celery_workers_health() -> dict[str, Any]:
    """Pings Celery workers via Redis broker with a strict timeout."""
    try:
        def _ping() -> Any:
            from app.workers.celery_app import celery_app
            return celery_app.control.ping(timeout=settings.CELERY_WORKER_PING_TIMEOUT)

        async with asyncio.timeout(settings.CELERY_WORKER_PING_TIMEOUT + 1.0):
            responses = await asyncio.to_thread(_ping)

        if responses:
            worker_names = []
            for resp in responses:
                if isinstance(resp, dict):
                    worker_names.extend(resp.keys())
            return {
                "status": "connected",
                "workers_online": len(worker_names),
                "workers": worker_names,
            }
        else:
            return {
                "status": "unavailable",
                "workers_online": 0,
                "message": "No active Celery workers responded to ping",
            }
    except Exception as e:
        logger.warning(f"Celery worker health check failed: {e}")
        return {
            "status": "disconnected",
            "workers_online": 0,
            "error": str(e),
        }


@router.get("/health", summary="Basic liveness probe")
@router.get("/health/live", summary="Explicit liveness probe")
async def health_check(request: Request) -> dict[str, Any]:
    """
    Returns basic application process liveness status.
    This check does not ping downstream dependencies and is intended for
    container orchestrator liveness checks (e.g., Kubernetes livenessProbe / Docker HEALTHCHECK).
    """
    request_id = get_request_id(request)
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "meta": {
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/health/ready", summary="Comprehensive readiness probe")
async def readiness_check(request: Request) -> JSONResponse:
    """
    Readiness probe validating connectivity to all core dependencies:
    - PostgreSQL database
    - Redis cache and rate limiter
    - Object storage (MinIO, Cloudflare R2, or AWS S3)
    - Celery task workers
    - ClamAV antivirus scanner daemon (if enabled)

    Clearly separates application process health from downstream dependency health.
    Returns HTTP 200 if the application can accept and process user traffic,
    or HTTP 503 if critical dependencies are unavailable.
    """
    request_id = get_request_id(request)

    # Gather dependency health statuses concurrently
    db_health, redis_health, storage_health, workers_health, scanner_health = (
        await asyncio.gather(
            check_database_health(),
            check_redis_health(),
            check_storage_health(),
            check_celery_workers_health(),
            check_scanner_health(),
            return_exceptions=False,
        )
    )

    dependencies = {
        "database": db_health,
        "redis": redis_health,
        "storage": storage_health,
        "workers": workers_health,
        "malware_scanner": scanner_health,
    }

    # Core dependencies required for basic operation
    core_healthy = (
        db_health.get("status") == "connected"
        and redis_health.get("status") == "connected"
        and storage_health.get("status") == "connected"
    )

    # Check scanner health if fail-closed is active
    scanner_healthy = True
    if settings.CLAMAV_ENABLED and settings.CLAMAV_FAIL_CLOSED:
        scanner_healthy = scanner_health.get("status") == "connected"

    # Worker readiness check: if in production, at least one worker is expected
    workers_ok = workers_health.get("status") == "connected"

    overall_ready = core_healthy and scanner_healthy and (workers_ok or settings.ENVIRONMENT != "production")

    if overall_ready:
        overall_status = "ready"
        http_status = status.HTTP_200_OK
    elif core_healthy and (not scanner_healthy or not workers_ok):
        overall_status = "degraded"
        # If scanner fail_closed is violated or no workers in production, 503
        if not scanner_healthy or (settings.ENVIRONMENT == "production" and not workers_ok):
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            http_status = status.HTTP_200_OK
    else:
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "success": overall_ready or (core_healthy and http_status == status.HTTP_200_OK),
            "data": {
                "status": overall_status,
                "application": {
                    "status": "healthy",
                    "service": settings.PROJECT_NAME,
                    "version": settings.VERSION,
                    "environment": settings.ENVIRONMENT,
                },
                "dependencies": dependencies,
                # Retain legacy 'services' key for backward compatibility
                "services": dependencies,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
    )
