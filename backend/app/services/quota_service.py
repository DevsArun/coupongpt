"""Search quota enforcement backed by Redis counters.

A user's plan defines a quota ``limit`` over a ``window`` (day or month). We keep
a Redis counter keyed by ``quota:{user_id}:{window}:{bucket}`` with a TTL that
expires at the end of the window, so counts reset automatically. Anonymous users
are limited by IP on a small daily allowance.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QuotaExceededError
from app.core.redis import get_redis
from app.models.billing import Plan, Subscription
from app.schemas.search import QuotaStatus

ANON_DAILY_LIMIT = 5


async def get_effective_plan(db: AsyncSession, user_id: int | None) -> Plan | None:
    """Resolve the plan that governs a user's quota.

    Uses the most recent active/trialing subscription; otherwise the public
    ``free`` plan.
    """
    if user_id is not None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status.in_(("active", "trialing")),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if sub and sub.plan:
            return sub.plan

    free = (await db.execute(select(Plan).where(Plan.slug == "free"))).scalar_one_or_none()
    return free


def _bucket_and_ttl(window: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    if window == "month":
        bucket = now.strftime("%Y-%m")
        # seconds to first of next month (approximate via 31-day cap is fine for TTL)
        if now.month == 12:
            nxt = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            nxt = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        ttl = int((nxt - now).total_seconds())
    else:  # day
        bucket = now.strftime("%Y-%m-%d")
        nxt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        nxt = nxt + timedelta(days=1)
        ttl = int((nxt - now).total_seconds())
    return bucket, max(ttl, 1)


def _key(scope: str, window: str, bucket: str) -> str:
    return f"quota:{scope}:{window}:{bucket}"


async def check_and_consume(
    db: AsyncSession, *, user_id: int | None, ip: str | None
) -> QuotaStatus:
    """Atomically consume one search unit, raising 429 if the quota is exhausted."""
    redis = get_redis()

    if user_id is None:
        window = "day"
        limit = ANON_DAILY_LIMIT
        plan_slug = "anonymous"
        scope = f"ip:{ip or 'unknown'}"
    else:
        plan = await get_effective_plan(db, user_id)
        limit = plan.quota_limit if plan else 10
        window = plan.quota_window if plan else "day"
        plan_slug = plan.slug if plan else "free"
        scope = f"user:{user_id}"

    bucket, ttl = _bucket_and_ttl(window)
    key = _key(scope, window, bucket)

    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, ttl)

    remaining = max(limit - used, 0)
    resets_in = await redis.ttl(key)

    if used > limit:
        # roll back the increment so we don't perpetually count over-limit hits
        await redis.decr(key)
        raise QuotaExceededError(
            "You have reached your search quota for this period.",
            detail={"plan": plan_slug, "limit": limit, "window": window},
        )

    return QuotaStatus(
        plan=plan_slug,
        limit=limit,
        window=window,
        used=used,
        remaining=remaining,
        resets_in_seconds=max(resets_in, 0),
    )


async def peek_quota(db: AsyncSession, *, user_id: int | None, ip: str | None) -> QuotaStatus:
    """Return current quota status without consuming a unit."""
    redis = get_redis()
    if user_id is None:
        window, limit, plan_slug, scope = "day", ANON_DAILY_LIMIT, "anonymous", f"ip:{ip or 'unknown'}"
    else:
        plan = await get_effective_plan(db, user_id)
        limit = plan.quota_limit if plan else 10
        window = plan.quota_window if plan else "day"
        plan_slug = plan.slug if plan else "free"
        scope = f"user:{user_id}"

    bucket, _ = _bucket_and_ttl(window)
    key = _key(scope, window, bucket)
    used = int(await redis.get(key) or 0)
    resets_in = await redis.ttl(key)
    return QuotaStatus(
        plan=plan_slug,
        limit=limit,
        window=window,
        used=used,
        remaining=max(limit - used, 0),
        resets_in_seconds=max(resets_in, 0),
    )
