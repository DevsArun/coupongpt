"""Health, readiness, and version endpoints used by load balancers and HF Spaces."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import settings
from app.core.database import ping_database
from app.core.redis import ping_redis
from app.search.client import ping_meilisearch

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    """Cheap liveness check — does not touch dependencies."""
    return {"status": "ok", "service": settings.app_name, "version": __version__}


@router.get("/ready", summary="Readiness probe")
async def ready() -> dict:
    """Readiness check — verifies connectivity to all backing services."""
    db_ok = await ping_database()
    redis_ok = await ping_redis()
    meili_ok = await ping_meilisearch()
    ready_ = db_ok and redis_ok and meili_ok
    return {
        "ready": ready_,
        "dependencies": {
            "mysql": "ok" if db_ok else "down",
            "redis": "ok" if redis_ok else "down",
            "meilisearch": "ok" if meili_ok else "down",
        },
    }


@router.get("/version", summary="Build/version info")
async def version() -> dict:
    return {
        "service": settings.app_name,
        "version": __version__,
        "environment": settings.app_env,
    }
