"""Network helpers — resolve the real client IP behind reverse proxies.

When the app sits behind a load balancer / reverse proxy (the common production
setup), ``request.client.host`` is the proxy's IP. If ``TRUST_PROXY_HEADERS`` is
enabled we honour the left-most address in ``X-Forwarded-For`` instead, which is
the original client. This keeps rate limiting and audit logging accurate.
"""
from __future__ import annotations

from starlette.requests import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str | None:
    if settings.trust_proxy_headers:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Left-most entry is the original client.
            first = xff.split(",")[0].strip()
            if first:
                return first
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else None
