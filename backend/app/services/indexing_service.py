"""Service that pushes coupons into Meilisearch.

Keeps MySQL (source of truth) and Meilisearch (search index) in sync. Only
``active`` coupons are indexed; expired/revoked coupons are removed.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.catalog import Merchant
from app.models.coupon import Coupon
from app.search import client as meili
from app.search.indexing import coupon_to_document

logger = get_logger("indexing_service")


async def _document_for(db: AsyncSession, coupon: Coupon) -> dict:
    merchant = coupon.merchant
    if merchant is None:
        merchant = (
            await db.execute(
                select(Merchant)
                .where(Merchant.id == coupon.merchant_id)
                .options(selectinload(Merchant.aliases))
            )
        ).scalar_one()
    aliases = [a.alias for a in merchant.aliases] if merchant.aliases else []
    return coupon_to_document(coupon, merchant, merchant_aliases=aliases)


async def index_coupon(db: AsyncSession, coupon: Coupon) -> None:
    if coupon.status != "active":
        await meili.delete_document(coupon.id)
        return
    doc = await _document_for(db, coupon)
    await meili.add_documents([doc])
    coupon.indexed_at = datetime.utcnow()
    await db.flush()


async def remove_coupon(coupon_id: int) -> None:
    await meili.delete_document(coupon_id)


async def reindex_all(db: AsyncSession, *, batch_size: int = 500) -> int:
    """Rebuild the index from all active coupons. Returns the number indexed."""
    await meili.ensure_index()
    stmt = (
        select(Coupon)
        .where(Coupon.status == "active")
        .options(selectinload(Coupon.merchant).selectinload(Merchant.aliases))
    )
    coupons = (await db.execute(stmt)).scalars().all()

    total = 0
    batch: list[dict] = []
    now = datetime.utcnow()
    for coupon in coupons:
        merchant = coupon.merchant
        aliases = [a.alias for a in merchant.aliases] if merchant and merchant.aliases else []
        batch.append(coupon_to_document(coupon, merchant, merchant_aliases=aliases))
        coupon.indexed_at = now
        if len(batch) >= batch_size:
            await meili.add_documents(batch)
            total += len(batch)
            batch = []
    if batch:
        await meili.add_documents(batch)
        total += len(batch)

    await db.flush()
    logger.info("reindex_complete", indexed=total)
    return total
