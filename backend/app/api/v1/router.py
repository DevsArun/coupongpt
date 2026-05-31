"""Aggregates all v1 endpoint routers.

Routers are added phase by phase. Each ``include_router`` line wires a feature
area into the versioned API surface.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

api_router.include_router(health.router)

# Feature routers (auth, search, coupons, billing, admin, user) are registered
# here as each phase lands. See app/api/v1/endpoints/.
