"""FastAPI application factory and lifespan management.

Wires configuration, logging, middleware, exception handlers, and the versioned
API router into a single ASGI app. The same app object runs on Hugging Face
Spaces, a VPS, or a dedicated server.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redis import close_redis

logger = get_logger("main")


def _init_sentry() -> None:
    """Initialise Sentry error tracking if a DSN is configured."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1,
            release=__version__,
        )
        logger.info("sentry_initialized")
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("sentry_init_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Fail fast in production if secrets/CORS are misconfigured.
    settings.validate_production()
    _init_sentry()
    logger.info("startup", env=settings.app_env, version=__version__)

    # Best-effort init of external services, each time-bounded so a slow/unreachable
    # managed service (common on first boot) never blocks the Space from going live.
    try:
        from app.search.client import ensure_index

        await asyncio.wait_for(ensure_index(), timeout=10)
    except Exception as exc:  # pragma: no cover - depends on live Meilisearch
        logger.warning("meili_init_skipped", error=str(exc))

    try:
        from app.core.database import SessionFactory
        from app.services.ai_service import refresh_router

        async def _init_ai() -> None:
            async with SessionFactory() as db:
                return await refresh_router(db)

        chain = await asyncio.wait_for(_init_ai(), timeout=10)
        logger.info("ai_router_configured", chain=chain)
    except Exception as exc:  # pragma: no cover - depends on live DB
        logger.warning("ai_router_init_skipped", error=str(exc))

    yield

    logger.info("shutdown")
    await close_redis()
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        description="AI Coupon Search SaaS — backend API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- Middleware (order matters: last added runs first) ----
    if settings.allowed_hosts_list != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()
