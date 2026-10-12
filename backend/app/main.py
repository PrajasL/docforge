from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    get_request_id,
    validation_exception_handler,
)
from app.core.logging import logger, setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import close_redis_client
from app.core.storage import storage_backend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    setup_logging(settings.LOG_LEVEL)
    from app.core.monitoring import init_monitoring
    init_monitoring()
    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.VERSION} "
        f"[{settings.ENVIRONMENT} mode]"
    )

    # Attempt to verify/create storage buckets asynchronously in background
    try:
        await storage_backend.ensure_buckets_exist()
    except Exception as e:
        logger.warning(f"Could not connect to storage during startup: {e}")

    yield

    # Graceful shutdown
    logger.info("Shutting down DocForge backend...")
    await close_redis_client()
    logger.info("Shutdown complete.")


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="High-performance, secure online PDF processing platform API.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
        docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
    )

    # Rate limiting middleware (atomic Redis sliding window)
    from app.core.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # Request context middleware (Request ID, timing, security headers)
    app.add_middleware(RequestContextMiddleware)

    # Centralized exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Root health endpoints for load balancers / container orchestrators
    app.include_router(health_router)

    # Versioned API routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["root"], summary="API Root")
    async def root_index(request: Request) -> dict[str, Any]:
        return {
            "success": True,
            "data": {
                "name": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
                "health": "/health",
                "ready": "/health/ready",
            },
            "meta": {
                "request_id": get_request_id(request),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }

    return app


app = create_application()
