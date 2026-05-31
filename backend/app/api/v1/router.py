"""Aggregates all v1 endpoint routers.

Routers are added phase by phase. Each ``include_router`` line wires a feature
area into the versioned API surface.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, coupons, health, me, merchants, search
from app.api.v1.endpoints.admin import admin_router

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(search.router)
api_router.include_router(coupons.router)
api_router.include_router(merchants.router)
api_router.include_router(me.router)
api_router.include_router(billing.router)
api_router.include_router(admin_router)
