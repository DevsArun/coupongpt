"""Public merchant endpoints: list and detail (used by the storefront + autocomplete)."""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.core.exceptions import NotFoundError
from app.models.catalog import Merchant
from app.schemas.common import Page
from app.schemas.merchant import MerchantOut

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=Page[MerchantOut])
async def list_merchants(
    db: DbSession,
    q: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
) -> Page[MerchantOut]:
    base = select(Merchant).where(Merchant.is_active.is_(True))
    if q:
        base = base.where(Merchant.name.ilike(f"%{q}%"))
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    stmt = base.order_by(Merchant.coupon_count.desc()).limit(page_size).offset((page - 1) * page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    return Page.create([MerchantOut.model_validate(r) for r in rows], total, page, page_size)


@router.get("/{slug}", response_model=MerchantOut)
async def get_merchant(slug: str, db: DbSession) -> MerchantOut:
    merchant = (
        await db.execute(select(Merchant).where(Merchant.slug == slug))
    ).scalar_one_or_none()
    if merchant is None:
        raise NotFoundError("Merchant not found.")
    return MerchantOut.model_validate(merchant)
