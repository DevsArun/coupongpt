"""FastAPI application factory and lifespan management.

Wires configuration, logging, middleware, exception handlers, and the versioned
API router into a single ASGI app. The same app object runs on Hugging Face
Spaces, a VPS, or a dedicated server.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", env=settings.app_env, version=__version__)

    # Best-effort: ensure the search index exists with the right settings.
    try:
        from app.search.client import ensure_index

        await ensure_index()
    except Exception as exc:  # pragma: no cover - depends on live Meilisearch
        logger.warning("meili_init_skipped", error=str(exc))

    # Best-effort: configure the AI router from DB provider settings.
    try:
        from app.core.database import SessionFactory
        from app.services.ai_service import refresh_router

        async with SessionFactory() as db:
            chain = await refresh_router(db)
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
