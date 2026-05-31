"""HTTP middleware: request IDs, timing, security headers, and rate limiting."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.utils.net import get_client_ip

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, bind logging context, and record latency."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = str(elapsed_ms)
        logger.info("request", status_code=response.status_code, latency_ms=elapsed_ms)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add a baseline set of security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Coarse per-IP rate limiting using a Redis fixed-window counter.

    Fine-grained per-user search quotas are enforced separately in the search
    service; this is a cheap first line of defence against abuse.
    """

    def __init__(self, app, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit_per_minute or settings.rate_limit_per_minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only rate limit API traffic; let docs/health pass freely.
        if not request.url.path.startswith(settings.api_v1_prefix):
            return await call_next(request)

        client_ip = get_client_ip(request) or "unknown"
        window = int(time.time() // 60)
        key = f"rl:{client_ip}:{window}"

        try:
            redis = get_redis()
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, 60)
            if current > self.limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many requests, slow down.",
                        }
                    },
                    headers={"Retry-After": "60"},
                )
        except Exception:
            # Fail open: never let a Redis hiccup take down the API.
            logger.warning("rate_limit_unavailable", ip=client_ip)

        return await call_next(request)
