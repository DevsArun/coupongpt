"""Admin dashboard endpoint — top-level mission control metrics."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_permission
from app.schemas.admin import DashboardResponse, DashboardStats
from app.services import admin_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    db: DbSession,
    _: object = Depends(require_permission("dashboard.view")),
) -> DashboardResponse:
    stats = await admin_service.dashboard_stats(db)
    return DashboardResponse(
        stats=DashboardStats(**stats),
        top_merchants=await admin_service.top_merchants(db),
        search_trend=await admin_service.search_trend(db),
    )
