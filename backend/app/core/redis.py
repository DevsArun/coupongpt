"""Async Redis client used for caching, quotas, rate-limiting, and queues.

A single connection pool is shared process-wide. All values are stored as UTF-8
strings (``decode_responses=True``) so callers work with plain ``str``.
"""
from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the shared Redis client, creating it lazily."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_uri,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
    return _redis


async def ping_redis() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
