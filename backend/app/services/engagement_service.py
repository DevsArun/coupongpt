"""User engagement service: saved coupons, watchlists, alerts, notifications, referrals."""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.catalog import Merchant
from app.models.coupon import Coupon
from app.models.engagement import (
    DealAlert,
    Notification,
    Referral,
    SavedCoupon,
    Watchlist,
)
from app.models.search import SearchQuery


# ----------------------------------------------------------------- saved
async def list_saved(db: AsyncSession, user_id: int) -> list[dict]:
    stmt = (
        select(SavedCoupon, Coupon, Merchant)
        .join(Coupon, Coupon.id == SavedCoupon.coupon_id)
        .join(Merchant, Merchant.id == Coupon.merchant_id)
        .where(SavedCoupon.user_id == user_id)
        .order_by(SavedCoupon.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": s.id,
            "coupon_uuid": c.uuid,
            "title": c.title,
            "code": c.code,
            "merchant_name": m.name,
            "discount_type": c.discount_type,
            "discount_value": float(c.discount_value) if c.discount_value is not None else None,
            "expires_at": c.expires_at,
            "saved_at": s.created_at,
        }
        for (s, c, m) in rows
    ]


async def save_coupon(db: AsyncSession, user_id: int, coupon_uuid: str) -> None:
    coupon = (await db.execute(select(Coupon).where(Coupon.uuid == coupon_uuid))).scalar_one_or_none()
    if coupon is None:
        raise NotFoundError("Coupon not found.")
    exists = (
        await db.execute(
            select(SavedCoupon).where(
                SavedCoupon.user_id == user_id, SavedCoupon.coupon_id == coupon.id
            )
        )
    ).scalar_one_or_none()
    if exists:
        return
    db.add(SavedCoupon(user_id=user_id, coupon_id=coupon.id))
    await db.flush()


async def unsave_coupon(db: AsyncSession, user_id: int, coupon_uuid: str) -> None:
    coupon = (await db.execute(select(Coupon).where(Coupon.uuid == coupon_uuid))).scalar_one_or_none()
    if coupon is None:
        return
    await db.execute(
        delete(SavedCoupon).where(
            SavedCoupon.user_id == user_id, SavedCoupon.coupon_id == coupon.id
        )
    )


# ------------------------------------------------------------- watchlist
async def list_watchlist(db: AsyncSession, user_id: int) -> list[dict]:
    stmt = (
        select(Watchlist, Merchant)
        .join(Merchant, Merchant.id == Watchlist.merchant_id)
        .where(Watchlist.user_id == user_id)
        .order_by(Watchlist.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": w.id,
            "merchant_id": m.id,
            "merchant_name": m.name,
            "merchant_slug": m.slug,
            "created_at": w.created_at,
        }
        for (w, m) in rows
    ]


async def add_watch(db: AsyncSession, user_id: int, merchant_id: int) -> None:
    merchant = (await db.execute(select(Merchant).where(Merchant.id == merchant_id))).scalar_one_or_none()
    if merchant is None:
        raise NotFoundError("Merchant not found.")
    exists = (
        await db.execute(
            select(Watchlist).where(Watchlist.user_id == user_id, Watchlist.merchant_id == merchant_id)
        )
    ).scalar_one_or_none()
    if exists:
        raise ConflictError("Already in your watchlist.")
    db.add(Watchlist(user_id=user_id, merchant_id=merchant_id))
    await db.flush()


async def remove_watch(db: AsyncSession, user_id: int, watch_id: int) -> None:
    await db.execute(
        delete(Watchlist).where(Watchlist.id == watch_id, Watchlist.user_id == user_id)
    )


# ----------------------------------------------------------------- alerts
async def list_alerts(db: AsyncSession, user_id: int) -> list[DealAlert]:
    stmt = select(DealAlert).where(DealAlert.user_id == user_id).order_by(DealAlert.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def create_alert(
    db: AsyncSession,
    user_id: int,
    *,
    merchant_id: int | None,
    keyword: str | None,
    min_discount: float | None,
    channel: str,
) -> DealAlert:
    if not merchant_id and not keyword:
        raise ConflictError("Provide a merchant or a keyword for the alert.")
    alert = DealAlert(
        user_id=user_id,
        merchant_id=merchant_id,
        keyword=keyword,
        min_discount=min_discount,
        channel=channel if channel in ("email", "push", "in_app") else "in_app",
    )
    db.add(alert)
    await db.flush()
    return alert


async def delete_alert(db: AsyncSession, user_id: int, alert_id: int) -> None:
    await db.execute(delete(DealAlert).where(DealAlert.id == alert_id, DealAlert.user_id == user_id))


# ---------------------------------------------------------- notifications
async def list_notifications(db: AsyncSession, user_id: int, *, limit: int = 50) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def unread_count(db: AsyncSession, user_id: int) -> int:
    stmt = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    )
    return int((await db.execute(stmt)).scalar_one())


async def mark_all_read(db: AsyncSession, user_id: int) -> None:
    from datetime import datetime

    from sqlalchemy import update

    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.utcnow())
    )


# ----------------------------------------------------------------- history
async def search_history(db: AsyncSession, user_id: int, *, limit: int = 50) -> list[SearchQuery]:
    stmt = (
        select(SearchQuery)
        .where(SearchQuery.user_id == user_id)
        .order_by(SearchQuery.created_at.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


# --------------------------------------------------------------- referrals
async def referral_summary(db: AsyncSession, user_id: int) -> dict:
    rows = (
        await db.execute(select(Referral.status, func.count()).where(Referral.referrer_id == user_id).group_by(Referral.status))
    ).all()
    counts = {status: int(n) for status, n in rows}
    return {
        "total": sum(counts.values()),
        "converted": counts.get("converted", 0) + counts.get("rewarded", 0),
        "rewarded": counts.get("rewarded", 0),
    }
