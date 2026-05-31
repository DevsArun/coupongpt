"""Admin coupon management, moderation, and validation/scoring controls."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import new_uuid
from app.models.coupon import Coupon
from app.schemas.common import Message, Page
from app.schemas.coupon import CouponCreate, CouponOut, CouponUpdate
from app.services import coupon_service, indexing_service
from app.services.audit_service import record_audit
from app.utils.text import content_hash, normalize_query

router = APIRouter()


@router.get("/coupons", response_model=Page[CouponOut])
async def list_coupons(
    db: DbSession,
    status: str | None = Query(None),
    merchant_id: int | None = Query(None),
    q: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("coupons.read")),
) -> Page[CouponOut]:
    base = select(Coupon)
    if status:
        base = base.where(Coupon.status == status)
    if merchant_id:
        base = base.where(Coupon.merchant_id == merchant_id)
    if q:
        base = base.where(Coupon.title.ilike(f"%{q}%"))
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(
            base.order_by(Coupon.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    return Page.create([CouponOut.model_validate(r) for r in rows], total, page, page_size)


@router.post("/coupons", response_model=CouponOut, status_code=201)
async def create_coupon(
    payload: CouponCreate,
    db: DbSession,
    user: CurrentUser,
    _: object = Depends(require_permission("coupons.write")),
) -> CouponOut:
    chash = content_hash(
        str(payload.merchant_id),
        (payload.code or "").upper(),
        payload.discount_type,
        str(payload.discount_value or ""),
        normalize_query(payload.title),
    )
    coupon = Coupon(
        uuid=new_uuid(),
        content_hash=chash,
        merchant_id=payload.merchant_id,
        title=payload.title,
        code=payload.code.upper() if payload.code else None,
        description=payload.description,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        currency=payload.currency,
        landing_url=payload.landing_url,
        terms=payload.terms,
        expires_at=payload.expires_at,
        status="active",
        confidence_score=0.8,
    )
    db.add(coupon)
    await db.flush()
    await coupon_service.rescore(db, coupon)
    await indexing_service.index_coupon(db, coupon)
    await record_audit(db, action="coupon.create", actor_id=user.id, entity_type="coupon", entity_id=coupon.id)
    return CouponOut.model_validate(coupon)


@router.patch("/coupons/{coupon_id}", response_model=CouponOut)
async def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    db: DbSession,
    user: CurrentUser,
    _: object = Depends(require_permission("coupons.write")),
) -> CouponOut:
    coupon = await coupon_service.get_by_id(db, coupon_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "code" and value:
            value = value.upper()
        setattr(coupon, field, value)
    await db.flush()
    await indexing_service.index_coupon(db, coupon)
    await record_audit(db, action="coupon.update", actor_id=user.id, entity_type="coupon", entity_id=coupon_id)
    return CouponOut.model_validate(coupon)


@router.post("/coupons/{coupon_id}/moderate", response_model=CouponOut)
async def moderate_coupon(
    coupon_id: int,
    db: DbSession,
    user: CurrentUser,
    action: str = Query(..., description="approve|reject"),
    _: object = Depends(require_permission("coupons.moderate")),
) -> CouponOut:
    coupon = await coupon_service.get_by_id(db, coupon_id)
    if action == "approve":
        coupon.status = "active"
        await db.flush()
        await indexing_service.index_coupon(db, coupon)
    elif action == "reject":
        coupon.status = "revoked"
        await db.flush()
        await indexing_service.remove_coupon(coupon.id)
    await record_audit(
        db, action=f"coupon.{action}", actor_id=user.id, entity_type="coupon", entity_id=coupon_id
    )
    return CouponOut.model_validate(coupon)


@router.post("/coupons/{coupon_id}/rescore", response_model=CouponOut)
async def rescore_coupon(
    coupon_id: int,
    db: DbSession,
    _: object = Depends(require_permission("validation.run")),
) -> CouponOut:
    coupon = await coupon_service.get_by_id(db, coupon_id)
    await coupon_service.rescore(db, coupon)
    await indexing_service.index_coupon(db, coupon)
    return CouponOut.model_validate(coupon)


@router.post("/coupons/reindex", response_model=Message)
async def reindex(
    db: DbSession,
    _: object = Depends(require_permission("validation.run")),
) -> Message:
    count = await indexing_service.reindex_all(db)
    return Message(message=f"Reindexed {count} coupons.")


@router.post("/coupons/expire-stale", response_model=Message)
async def expire_stale(
    db: DbSession,
    _: object = Depends(require_permission("validation.run")),
) -> Message:
    n = await coupon_service.expire_stale(db)
    return Message(message=f"Expired {n} stale coupons.")
