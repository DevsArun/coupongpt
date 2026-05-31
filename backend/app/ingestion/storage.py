"""Storage stage — persist a structured coupon with computed scores, then index.

Brings together dedup, the validation engine, and the scoring blend:

    structured coupon ─► dedup (hash + near-dup count)
                       ─► validation.all_scores(...)
                       ─► scoring.compute_ranking_score(...)
                       ─► upsert Coupon row
                       ─► record validation event
                       ─► (status==active) push to Meilisearch
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import new_uuid
from app.ingestion import dedup, scoring, validation
from app.ingestion.extraction import StructuredCoupon
from app.models.coupon import Coupon, CouponValidationEvent
from app.services import indexing_service

logger = get_logger("ingestion.storage")


async def store_coupon(
    db: AsyncSession,
    sc: StructuredCoupon,
    *,
    merchant_id: int,
    merchant_known: bool,
    merchant_trust: float | None,
    source_id: int | None,
    source_trust: float | None,
    auto_activate: bool = True,
    index: bool = True,
) -> tuple[Coupon, bool]:
    """Upsert a coupon. Returns (coupon, created)."""
    chash = dedup.compute_content_hash(merchant_id, sc)
    existing = await dedup.find_existing(db, chash)
    near_dups = await dedup.count_near_duplicates(db, merchant_id, sc, exclude_hash=chash)

    scores = validation.all_scores(
        source_trust=source_trust,
        merchant_trust=merchant_trust,
        last_seen=datetime.utcnow(),
        has_code=bool(sc.code),
        has_discount_value=sc.discount_value is not None,
        merchant_known=merchant_known,
        ai_confidence=sc.confidence,
        duplicate_count=near_dups,
        success_reports=existing.success_reports if existing else 0,
        fail_reports=existing.fail_reports if existing else 0,
        expires_at=sc.expires_at,
    )
    ranking = scoring.compute_ranking_score(scores)

    created = existing is None
    coupon = existing or Coupon(uuid=new_uuid(), content_hash=chash, merchant_id=merchant_id)

    coupon.title = sc.title
    coupon.description = coupon.description or sc.raw_text[:500] or None
    coupon.code = sc.code.upper() if sc.code else None
    coupon.discount_type = sc.discount_type
    coupon.discount_value = sc.discount_value
    coupon.currency = sc.currency
    coupon.landing_url = sc.landing_url
    coupon.terms = sc.terms
    coupon.source_id = source_id
    coupon.expires_at = sc.expires_at
    for key, value in scores.items():
        setattr(coupon, key, value)
    old_rank = float(coupon.ranking_score) if existing else None
    coupon.ranking_score = ranking

    # Decide status: expired coupons are marked expired; otherwise activate.
    if sc.expires_at and sc.expires_at <= datetime.utcnow():
        coupon.status = "expired"
    elif auto_activate and sc.confidence >= 0.5:
        coupon.status = "active"
    elif created:
        coupon.status = "pending_review"

    if created:
        db.add(coupon)
    await db.flush()

    db.add(
        CouponValidationEvent(
            coupon_id=coupon.id,
            event_type="scored" if created else "revalidated",
            old_score=old_rank,
            new_score=ranking,
            detail={"scores": scores, "near_duplicates": near_dups},
        )
    )
    await db.flush()

    if index:
        try:
            await indexing_service.index_coupon(db, coupon)
        except Exception as exc:  # noqa: BLE001 - indexing is best-effort here
            logger.warning("index_on_store_failed", coupon_id=coupon.id, error=str(exc))

    return coupon, created
