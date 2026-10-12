import asyncio
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger

_redis_client: aioredis.Redis | None = None
_redis_loop: asyncio.AbstractEventLoop | None = None


def get_redis_client() -> aioredis.Redis:
    """Returns or initializes the global async Redis client."""
    global _redis_client, _redis_loop
    try:
        current_loop = asyncio.get_running_loop()
        if _redis_client is not None:
            if _redis_loop is None or _redis_loop.is_closed() or _redis_loop != current_loop:
                _redis_client = None
                _redis_loop = None
    except Exception:
        pass

    if _redis_client is None:
        try:
            _redis_loop = asyncio.get_running_loop()
        except Exception:
            _redis_loop = None

        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=3.0,
            socket_connect_timeout=3.0,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Closes Redis client connections."""
    global _redis_client, _redis_loop
    if _redis_client is not None:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None
        _redis_loop = None


async def check_redis_health() -> dict[str, Any]:
    """Checks Redis connectivity and returns status."""
    try:
        async with asyncio.timeout(3.0):
            client = get_redis_client()
            pong = await client.ping()
            if pong:
                return {"status": "connected"}
            return {"status": "error", "error": "Redis PING returned False"}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {"status": "disconnected", "error": str(e)}


def get_job_progress_channel(job_id: str) -> str:
    """Returns the Redis pubsub channel name for a job."""
    return f"job_progress:{job_id}"


async def publish_job_progress(job_id: str, data: dict[str, Any]) -> None:
    """Publishes a job progress update to Redis Pub/Sub."""
    try:
        import json
        client = get_redis_client()
        channel = get_job_progress_channel(job_id)
        payload = json.dumps(data)
        await client.publish(channel, payload)
    except Exception as e:
        logger.warning(f"Failed to publish progress update for job {job_id} to Redis: {e}")

