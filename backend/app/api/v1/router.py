"""Aggregates all v1 endpoint routers.

Routers are added phase by phase. Each ``include_router`` line wires a feature
area into the versioned API surface.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, search

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(search.router)

# Feature routers (coupons, billing, admin, user) are registered
# here as each phase lands. See app/api/v1/endpoints/.
