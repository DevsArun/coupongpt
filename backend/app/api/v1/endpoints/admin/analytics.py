"""Admin analytics: search analytics and revenue analytics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_permission
from app.services import admin_service

router = APIRouter()


@router.get("/analytics/search")
async def search_analytics(
    db: DbSession,
    days: int = Query(14, ge=1, le=90),
    _: object = Depends(require_permission("analytics.search")),
) -> dict:
    return {
        "trend": await admin_service.search_trend(db, days=days),
        "top_queries": await admin_service.top_queries(db, days=min(days, 30)),
        "zero_result_queries": await admin_service.zero_result_queries(db, days=min(days, 30)),
    }


@router.get("/analytics/revenue")
async def revenue_analytics(
    db: DbSession,
    months: int = Query(6, ge=1, le=24),
    _: object = Depends(require_permission("analytics.revenue")),
) -> dict:
    return {
        "monthly": await admin_service.revenue_breakdown(db, months=months),
    }
