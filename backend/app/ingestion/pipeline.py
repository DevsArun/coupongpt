"""Pipeline orchestrator — runs a source end-to-end.

    Source ─► Crawler ─► Cleaner ─► Extraction/AI Structuring
           ─► Deduplication ─► Validation ─► Scoring ─► Storage ─► Index

Progress and outcomes are recorded on a :class:`CrawlJob` so the admin queue view
can show exactly what each run produced.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.ingestion import cleaner, crawler, storage, structuring
from app.ingestion.extraction import looks_like_coupon
from app.models.catalog import Merchant
from app.models.ingestion import CrawlJob, Source

logger = get_logger("ingestion.pipeline")


async def _merchant_for(db: AsyncSession, source: Source) -> Merchant | None:
    if source.merchant_id is None:
        return None
    return (
        await db.execute(select(Merchant).where(Merchant.id == source.merchant_id))
    ).scalar_one_or_none()


async def _candidate_texts(fetch: crawler.FetchResult, source: Source) -> list[tuple[str, str | None]]:
    """Return [(text, url)] candidate blocks based on the source type."""
    ctype = (fetch.content_type or "").lower()
    candidates: list[tuple[str, str | None]] = []

    if source.type == "rss" or "xml" in ctype and "<rss" in fetch.text.lower():
        for item in crawler.parse_rss(fetch.text):
            text = f"{item.get('title','')}\n{item.get('summary','')}"
            candidates.append((cleaner.clean_html(text), item.get("link") or source.url))
    elif source.type == "sitemap" or "<urlset" in fetch.text.lower():
        # Sitemaps yield URLs; we record them but do not deep-crawl here (bounded run).
        for loc in crawler.parse_sitemap(fetch.text)[:50]:
            candidates.append((loc, loc))
    else:
        cleaned = cleaner.clean_html(fetch.text)
        for block in cleaner.chunk_candidates(cleaned):
            candidates.append((block, fetch.url))

    return candidates


async def run_source(db: AsyncSession, source: Source, *, use_ai: bool = True, max_items: int = 200) -> CrawlJob:
    job = CrawlJob(source_id=source.id, status="running", stage="crawl", started_at=datetime.utcnow())
    db.add(job)
    await db.flush()

    merchant = await _merchant_for(db, source)
    merchant_name = merchant.name if merchant else "Unknown"

    try:
        fetch = await crawler.fetch_url(source.url)
        if not fetch.ok:
            job.status = "failed"
            job.error = f"Fetch failed with status {fetch.status}"
            job.finished_at = datetime.utcnow()
            source.last_status = "fetch_failed"
            source.last_crawled_at = datetime.utcnow()
            await db.flush()
            return job

        job.stage = "extract"
        candidates = await _candidate_texts(fetch, source)
        job.items_found = len(candidates)

        ingested = 0
        for text, url in candidates[:max_items]:
            if source.type != "sitemap" and not looks_like_coupon(text):
                continue
            sc = await structuring.structure_coupon(
                text, merchant_name=merchant_name, url=url, use_ai=use_ai
            )
            if sc is None or merchant is None:
                continue
            job.stage = "store"
            _coupon, created = await storage.store_coupon(
                db,
                sc,
                merchant_id=merchant.id,
                merchant_known=True,
                merchant_trust=float(merchant.trust_score),
                source_id=source.id,
                source_trust=float(source.trust_score),
            )
            if created:
                ingested += 1

        job.items_ingested = ingested
        job.status = "succeeded"
        job.finished_at = datetime.utcnow()
        source.last_status = "ok"
        source.last_crawled_at = datetime.utcnow()
        if merchant:
            merchant.coupon_count = (merchant.coupon_count or 0) + ingested
        await db.flush()
        logger.info("pipeline_done", source_id=source.id, found=job.items_found, ingested=ingested)
        return job

    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = datetime.utcnow()
        source.last_status = "error"
        source.last_crawled_at = datetime.utcnow()
        await db.flush()
        logger.error("pipeline_failed", source_id=source.id, error=str(exc))
        return job


async def run_due_sources(db: AsyncSession, *, limit: int = 20, use_ai: bool = True) -> list[int]:
    """Run all due sources; returns the list of crawl job ids created."""
    from app.ingestion.discovery import due_sources

    sources = await due_sources(db, limit=limit)
    job_ids: list[int] = []
    for source in sources:
        # ensure aliases/merchant are loadable lazily within the session
        job = await run_source(db, source, use_ai=use_ai)
        job_ids.append(job.id)
    return job_ids
