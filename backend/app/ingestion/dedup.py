"""Deduplication stage.

A coupon's identity is a content hash over (merchant, normalized code, discount
type/value, normalized title). Exact-hash collisions are true duplicates. We also
count near-duplicates within a merchant (same code OR same title+discount) to
feed the ``duplicate_score``.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.extraction import StructuredCoupon
from app.models.coupon import Coupon
from app.utils.text import content_hash, normalize_query


def compute_content_hash(merchant_id: int, sc: StructuredCoupon) -> str:
    return content_hash(
        str(merchant_id),
        (sc.code or "").upper(),
        sc.discount_type,
        str(sc.discount_value or ""),
        normalize_query(sc.title),
    )


async def find_existing(db: AsyncSession, content_hash_value: str) -> Coupon | None:
    stmt = select(Coupon).where(Coupon.content_hash == content_hash_value)
    return (await db.execute(stmt)).scalar_one_or_none()


async def count_near_duplicates(
    db: AsyncSession, merchant_id: int, sc: StructuredCoupon, *, exclude_hash: str
) -> int:
    """Count other coupons for the merchant that look like this one."""
    conditions = []
    if sc.code:
        conditions.append(Coupon.code == sc.code.upper())
    conditions.append(Coupon.title == sc.title)

    if not conditions:
        return 0

    stmt = (
        select(func.count())
        .select_from(Coupon)
        .where(
            Coupon.merchant_id == merchant_id,
            Coupon.content_hash != exclude_hash,
            or_(*conditions),
        )
    )
    return int((await db.execute(stmt)).scalar_one())
