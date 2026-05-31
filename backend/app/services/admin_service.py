"""Admin aggregation queries powering the mission-control dashboard & analytics."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Payment, Subscription
from app.models.catalog import Merchant
from app.models.coupon import Coupon
from app.models.ingestion import CrawlJob, Source
from app.models.search import SearchQuery
from app.models.user import User


async def _count(db: AsyncSession, stmt) -> int:
    return int((await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())


async def dashboard_stats(db: AsyncSession) -> dict:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)

    users_total = await _count(db, select(User.id))
    coupons_total = await _count(db, select(Coupon.id))
    coupons_active = await _count(db, select(Coupon.id).where(Coupon.status == "active"))
    coupons_pending = await _count(
        db, select(Coupon.id).where(Coupon.status == "pending_review")
    )
    merchants_total = await _count(db, select(Merchant.id))
    sources_total = await _count(db, select(Source.id))
    searches_today = await _count(
        db, select(SearchQuery.id).where(SearchQuery.created_at >= today)
    )
    active_subs = await _count(
        db, select(Subscription.id).where(Subscription.status == "active")
    )

    revenue_month = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(
                Payment.status == "succeeded", Payment.paid_at >= month_start
            )
        )
    ).scalar_one()

    avg_latency = (
        await db.execute(
            select(func.coalesce(func.avg(SearchQuery.latency_ms), 0)).where(
                SearchQuery.created_at >= today
            )
        )
    ).scalar_one()

    return {
        "users_total": users_total,
        "coupons_total": coupons_total,
        "coupons_active": coupons_active,
        "coupons_pending": coupons_pending,
        "merchants_total": merchants_total,
        "sources_total": sources_total,
        "searches_today": searches_today,
        "active_subscriptions": active_subs,
        "revenue_month_cents": int(revenue_month or 0),
        "avg_search_latency_ms": round(float(avg_latency or 0), 1),
    }


async def top_merchants(db: AsyncSession, *, limit: int = 8) -> list[dict]:
    stmt = (
        select(Merchant.name, Merchant.slug, Merchant.coupon_count)
        .order_by(Merchant.coupon_count.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [{"name": r[0], "slug": r[1], "coupon_count": r[2]} for r in rows]


async def search_trend(db: AsyncSession, *, days: int = 14) -> list[dict]:
    """Daily search counts for the last N days."""
    since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    stmt = (
        select(func.date(SearchQuery.created_at).label("d"), func.count().label("c"))
        .where(SearchQuery.created_at >= since)
        .group_by("d")
        .order_by("d")
    )
    rows = (await db.execute(stmt)).all()
    return [{"date": str(r[0]), "count": int(r[1])} for r in rows]


async def top_queries(db: AsyncSession, *, limit: int = 10, days: int = 7) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(SearchQuery.normalized_query, func.count().label("c"))
        .where(SearchQuery.created_at >= since, SearchQuery.normalized_query.is_not(None))
        .group_by(SearchQuery.normalized_query)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [{"query": r[0], "count": int(r[1])} for r in rows]


async def zero_result_queries(db: AsyncSession, *, limit: int = 10, days: int = 7) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(SearchQuery.normalized_query, func.count().label("c"))
        .where(
            SearchQuery.created_at >= since,
            SearchQuery.results_count == 0,
            SearchQuery.normalized_query.is_not(None),
        )
        .group_by(SearchQuery.normalized_query)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [{"query": r[0], "count": int(r[1])} for r in rows]


async def revenue_breakdown(db: AsyncSession, *, months: int = 6) -> list[dict]:
    since = (datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
             - timedelta(days=31 * (months - 1)))
    stmt = (
        select(
            func.date_format(Payment.paid_at, "%Y-%m").label("m"),
            func.coalesce(func.sum(Payment.amount_cents), 0).label("total"),
            func.count().label("c"),
        )
        .where(Payment.status == "succeeded", Payment.paid_at >= since)
        .group_by("m")
        .order_by("m")
    )
    rows = (await db.execute(stmt)).all()
    return [{"month": r[0], "revenue_cents": int(r[1]), "payments": int(r[2])} for r in rows]


async def recent_crawl_jobs(db: AsyncSession, *, limit: int = 20) -> list[CrawlJob]:
    stmt = select(CrawlJob).order_by(CrawlJob.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())
