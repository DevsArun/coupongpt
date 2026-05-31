"""Admin catalog management: merchants, aliases, sources, and crawlers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import DbSession, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.ingestion import discovery, pipeline
from app.models.catalog import Merchant, MerchantAlias
from app.models.ingestion import Source
from app.schemas.admin import CrawlJobOut, SourceCreate, SourceOut
from app.schemas.common import Message, Page
from app.schemas.merchant import AliasCreate, MerchantCreate, MerchantOut, MerchantUpdate
from app.services import admin_service, merchant_service
from app.utils.text import slugify

router = APIRouter()


# ---------------------------------------------------------------- merchants
@router.get("/merchants", response_model=Page[MerchantOut])
async def list_merchants(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("merchants.read")),
) -> Page[MerchantOut]:
    base = select(Merchant)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(base.order_by(Merchant.name).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()
    return Page.create([MerchantOut.model_validate(r) for r in rows], total, page, page_size)


@router.post("/merchants", response_model=MerchantOut, status_code=201)
async def create_merchant(
    payload: MerchantCreate,
    db: DbSession,
    _: object = Depends(require_permission("merchants.write")),
) -> MerchantOut:
    slug = slugify(payload.slug)
    exists = (await db.execute(select(Merchant).where(Merchant.slug == slug))).scalar_one_or_none()
    if exists:
        raise ConflictError("A merchant with this slug already exists.")
    merchant = Merchant(
        slug=slug,
        name=payload.name,
        domain=payload.domain,
        logo_url=payload.logo_url,
        description=payload.description,
        trust_score=payload.trust_score,
    )
    db.add(merchant)
    await db.flush()
    await merchant_service.get_alias_index(db, force=True)
    return MerchantOut.model_validate(merchant)


@router.patch("/merchants/{merchant_id}", response_model=MerchantOut)
async def update_merchant(
    merchant_id: int,
    payload: MerchantUpdate,
    db: DbSession,
    _: object = Depends(require_permission("merchants.write")),
) -> MerchantOut:
    merchant = (await db.execute(select(Merchant).where(Merchant.id == merchant_id))).scalar_one_or_none()
    if merchant is None:
        raise NotFoundError("Merchant not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(merchant, field, value)
    await db.flush()
    await merchant_service.get_alias_index(db, force=True)
    return MerchantOut.model_validate(merchant)


@router.post("/merchants/{merchant_id}/aliases", response_model=Message, status_code=201)
async def add_alias(
    merchant_id: int,
    payload: AliasCreate,
    db: DbSession,
    _: object = Depends(require_permission("merchants.write")),
) -> Message:
    merchant = (await db.execute(select(Merchant).where(Merchant.id == merchant_id))).scalar_one_or_none()
    if merchant is None:
        raise NotFoundError("Merchant not found.")
    db.add(MerchantAlias(merchant_id=merchant_id, alias=payload.alias, weight=payload.weight))
    await db.flush()
    await merchant_service.get_alias_index(db, force=True)
    return Message(message="Alias added.")


# ---------------------------------------------------------------- sources
@router.get("/sources", response_model=Page[SourceOut])
async def list_sources(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("sources.read")),
) -> Page[SourceOut]:
    base = select(Source)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(base.order_by(Source.id.desc()).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()
    return Page.create([SourceOut.model_validate(r) for r in rows], total, page, page_size)


@router.post("/sources", response_model=SourceOut, status_code=201)
async def create_source(
    payload: SourceCreate,
    db: DbSession,
    _: object = Depends(require_permission("sources.write")),
) -> SourceOut:
    source, _created = await discovery.register_source(
        db,
        url=payload.url,
        type=payload.type,
        merchant_id=payload.merchant_id,
        trust_score=payload.trust_score,
        crawl_frequency=payload.crawl_frequency,
    )
    return SourceOut.model_validate(source)


@router.post("/sources/{source_id}/run", response_model=CrawlJobOut)
async def run_source(
    source_id: int,
    db: DbSession,
    use_ai: bool = Query(True),
    _: object = Depends(require_permission("crawlers.run")),
) -> CrawlJobOut:
    source = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if source is None:
        raise NotFoundError("Source not found.")
    job = await pipeline.run_source(db, source, use_ai=use_ai)
    return CrawlJobOut.model_validate(job)


# ---------------------------------------------------------------- crawlers/jobs
@router.get("/crawl-jobs", response_model=list[CrawlJobOut])
async def list_crawl_jobs(
    db: DbSession,
    _: object = Depends(require_permission("queues.read")),
) -> list[CrawlJobOut]:
    jobs = await admin_service.recent_crawl_jobs(db)
    return [CrawlJobOut.model_validate(j) for j in jobs]
