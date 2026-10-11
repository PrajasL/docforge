import time
import uuid
from typing import Optional, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.redis import get_redis_client


# Atomic sliding window script executed in Redis
LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local req_id = ARGV[4]
local clear_before = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, now .. '-' .. req_id)
    redis.call('EXPIRE', key, math.ceil(window) + 1)
    return {1, limit - count - 1, 0, math.ceil(now + window)}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if #oldest >= 2 then
        retry_after = math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
    end
    return {0, 0, retry_after, math.ceil(now + retry_after)}
end
"""


def resolve_client_ip(request: Request, trusted_proxies: Optional[List[str]] = None) -> str:
    """
    Safely resolves the client IP address.
    Only trusts X-Forwarded-For if the immediate connection peer is in trusted_proxies.
    Prevents IP spoofing attacks via arbitrary header forgery.
    """
    trusted = set(trusted_proxies or settings.TRUSTED_PROXIES)
    peer_ip = request.client.host if request.client else "127.0.0.1"

    if peer_ip in trusted:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Format: client, proxy1, proxy2
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if ips:
                # Walk from right to left, find first untrusted IP
                for ip in reversed(ips):
                    if ip not in trusted:
                        return ip
                return ips[0]

        # Alternative standard header
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip and x_real_ip.strip():
            return x_real_ip.strip()

    return peer_ip


class RateLimiter:
    """
    Redis-backed atomic sliding window rate limiter.
    """

    def __init__(self):
        self._script_sha: Optional[str] = None

    async def check(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> Tuple[bool, int, int, int]:
        """
        Executes atomic sliding window check against Redis.
        Returns: (allowed, remaining, retry_after, reset_time)
        """
        try:
            client = await get_redis_client()
            now = time.time()
            req_id = uuid.uuid4().hex[:8]

            res = await client.eval(
                LUA_SLIDING_WINDOW,
                1,
                key,
                str(now),
                str(window),
                str(limit),
                req_id,
            )
            # res format: [allowed (1/0), remaining, retry_after, reset_time]
            allowed = bool(res[0])
            remaining = int(res[1])
            retry_after = int(res[2])
            reset_time = int(res[3])
            return allowed, remaining, retry_after, reset_time
        except Exception as e:
            logger.warning(f"[RateLimiter] Redis failure during rate limit check for {key}: {e}")
            # Fail open for rate limiting if Redis connection drops, to avoid service outage
            return True, limit, 0, int(time.time() + window)


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying atomic rate limiting to API endpoints.
    Protects job creation, direct uploads, and API operations against abuse.
    Excludes Server-Sent Events (SSE) progress streams and health checks.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        method = request.method

        # 1. Skip preflights and excluded endpoints
        if method == "OPTIONS":
            return await call_next(request)

        if path.startswith("/health") or path.endswith("/progress") or path in ("/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        # Only rate-limit API routes
        if not path.startswith(settings.API_V1_PREFIX):
            return await call_next(request)

        client_ip = resolve_client_ip(request)

        # 2. Determine rate limit tier
        tier = "general"
        limit = settings.RATE_LIMIT_GENERAL_LIMIT
        window = settings.RATE_LIMIT_GENERAL_WINDOW

        if path == f"{settings.API_V1_PREFIX}/jobs" and method == "POST":
            tier = "job_creation"
            limit = settings.RATE_LIMIT_JOB_CREATION_LIMIT
            window = settings.RATE_LIMIT_JOB_CREATION_WINDOW
        elif "/files/" in path and method in ("POST", "PUT"):
            tier = "upload"
            limit = settings.RATE_LIMIT_UPLOAD_LIMIT
            window = settings.RATE_LIMIT_UPLOAD_WINDOW

        rate_key = f"rate_limit:{tier}:{client_ip}"
        allowed, remaining, retry_after, reset_time = await rate_limiter.check(
            rate_key, limit=limit, window=window
        )

        if not allowed:
            logger.warning(
                f"[RateLimiter] Rate limit exceeded for {client_ip} on {method} {path} "
                f"(tier={tier}, limit={limit}/{window}s). Retry-After: {retry_after}s"
            )
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                    },
                    "meta": {
                        "retry_after": retry_after,
                        "limit": limit,
                    },
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        return response
