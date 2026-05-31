"""Source discovery stage — register and prioritize ingestion sources.

Creates :class:`Source` rows for merchant offer/promo pages, RSS feeds, sitemaps,
newsletters, and user submissions, deduplicated by URL hash.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion import Source
from app.utils.text import sha256_hex


async def register_source(
    db: AsyncSession,
    *,
    url: str,
    type: str,
    merchant_id: int | None = None,
    trust_score: float = 0.5,
    crawl_frequency: int = 86400,
) -> tuple[Source, bool]:
    """Register a source idempotently (by URL hash). Returns (source, created)."""
    url_hash = sha256_hex(url.strip().lower())
    existing = (
        await db.execute(select(Source).where(Source.url_hash == url_hash))
    ).scalar_one_or_none()
    if existing:
        return existing, False

    source = Source(
        merchant_id=merchant_id,
        type=type,
        url=url.strip(),
        url_hash=url_hash,
        trust_score=trust_score,
        crawl_frequency=crawl_frequency,
        is_active=True,
    )
    db.add(source)
    await db.flush()
    return source, True


async def due_sources(db: AsyncSession, *, limit: int = 50) -> list[Source]:
    """Return active sources ordered by how overdue a crawl is (oldest first)."""
    stmt = (
        select(Source)
        .where(Source.is_active.is_(True))
        .order_by(Source.last_crawled_at.is_(None).desc(), Source.last_crawled_at.asc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
