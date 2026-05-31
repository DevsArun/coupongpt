"""Coupon CRUD, lookups, click/feedback tracking, and re-scoring."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import new_uuid
from app.ingestion import scoring, validation
from app.models.coupon import Coupon, CouponFeedback, CouponValidationEvent
from app.utils.text import content_hash, normalize_query


async def get_by_uuid(db: AsyncSession, uuid: str) -> Coupon | None:
    return (
        await db.execute(select(Coupon).where(Coupon.uuid == uuid))
    ).scalar_one_or_none()


async def get_by_id(db: AsyncSession, coupon_id: int) -> Coupon:
    coupon = (
        await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    ).scalar_one_or_none()
    if coupon is None:
        raise NotFoundError("Coupon not found.")
    return coupon


async def list_by_merchant(
    db: AsyncSession, merchant_id: int, *, limit: int = 20, offset: int = 0, active_only: bool = True
) -> tuple[list[Coupon], int]:
    base = select(Coupon).where(Coupon.merchant_id == merchant_id)
    if active_only:
        base = base.where(Coupon.status == "active")
    total = int(
        (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    )
    stmt = base.order_by(Coupon.ranking_score.desc()).limit(limit).offset(offset)
    rows = list((await db.execute(stmt)).scalars().all())
    return rows, total


async def register_view(db: AsyncSession, coupon_id: int) -> None:
    await db.execute(
        update(Coupon).where(Coupon.id == coupon_id).values(views=Coupon.views + 1)
    )


async def register_click(db: AsyncSession, coupon_id: int) -> Coupon:
    await db.execute(
        update(Coupon).where(Coupon.id == coupon_id).values(clicks=Coupon.clicks + 1)
    )
    return await get_by_id(db, coupon_id)


async def submit_feedback(
    db: AsyncSession, coupon_id: int, *, worked: bool, user_id: int | None, comment: str | None
) -> Coupon:
    coupon = await get_by_id(db, coupon_id)
    db.add(CouponFeedback(coupon_id=coupon_id, user_id=user_id, worked=worked, comment=comment))
    if worked:
        coupon.success_reports += 1
    else:
        coupon.fail_reports += 1
    await db.flush()
    await rescore(db, coupon)
    return coupon


async def rescore(db: AsyncSession, coupon: Coupon, *, merchant_trust: float | None = None) -> Coupon:
    """Recompute component scores + ranking score for an existing coupon."""
    scores = validation.all_scores(
        source_trust=float(coupon.source_trust_score),
        merchant_trust=merchant_trust if merchant_trust is not None else float(coupon.source_trust_score),
        last_seen=coupon.updated_at or coupon.created_at,
        has_code=bool(coupon.code),
        has_discount_value=coupon.discount_value is not None,
        merchant_known=True,
        ai_confidence=float(coupon.confidence_score),
        duplicate_count=0,
        success_reports=coupon.success_reports,
        fail_reports=coupon.fail_reports,
        expires_at=coupon.expires_at,
    )
    # Preserve trust + confidence + duplicate already established; refresh dynamic ones.
    coupon.freshness_score = scores["freshness_score"]
    coupon.success_rate_score = scores["success_rate_score"]
    coupon.expiry_score = scores["expiry_score"]
    old = float(coupon.ranking_score)
    current = {
        "source_trust_score": float(coupon.source_trust_score),
        "freshness_score": coupon.freshness_score,
        "confidence_score": float(coupon.confidence_score),
        "duplicate_score": float(coupon.duplicate_score),
        "success_rate_score": coupon.success_rate_score,
        "expiry_score": coupon.expiry_score,
    }
    coupon.ranking_score = scoring.compute_ranking_score(current)
    db.add(
        CouponValidationEvent(
            coupon_id=coupon.id, event_type="revalidated", old_score=old, new_score=coupon.ranking_score
        )
    )
    await db.flush()
    return coupon


async def expire_stale(db: AsyncSession) -> int:
    """Mark coupons past their expiry as expired. Returns the count updated."""
    result = await db.execute(
        update(Coupon)
        .where(Coupon.status == "active", Coupon.expires_at.is_not(None), Coupon.expires_at <= datetime.utcnow())
        .values(status="expired")
    )
    return result.rowcount or 0


def build_content_hash(merchant_id: int, title: str, code: str | None, discount_type: str, discount_value) -> str:
    return content_hash(
        str(merchant_id), (code or "").upper(), discount_type, str(discount_value or ""), normalize_query(title)
    )
