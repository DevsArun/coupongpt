"""Admin (mission control) API — aggregates all admin sub-routers under /admin."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.admin import (
    ai,
    analytics,
    catalog,
    coupons,
    dashboard,
    system,
    users,
)

admin_router = APIRouter(prefix="/admin", tags=["admin"])
admin_router.include_router(dashboard.router)
admin_router.include_router(catalog.router)
admin_router.include_router(coupons.router)
admin_router.include_router(ai.router)
admin_router.include_router(analytics.router)
admin_router.include_router(users.router)
admin_router.include_router(system.router)
