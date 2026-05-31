"""Merchant catalog service + typo-tolerant merchant resolution.

Builds an in-process alias index (merchant slug, name, and configured aliases)
that maps normalized strings to merchants. Resolution first tries exact alias
matches, then falls back to fuzzy matching (edit-distance similarity) so queries
like "niek" or "amazn" still resolve to the right brand.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Merchant
from app.utils.text import normalize_query, similarity, tokenize

_FUZZY_THRESHOLD = 0.74
_CACHE_TTL = 300  # seconds


@dataclass
class MerchantRef:
    id: int
    slug: str
    name: str


@dataclass
class _AliasEntry:
    merchant: MerchantRef
    weight: float


_alias_index: dict[str, _AliasEntry] = {}
_alias_index_built_at: float = 0.0


async def _build_alias_index(db: AsyncSession) -> dict[str, _AliasEntry]:
    stmt = (
        select(Merchant)
        .where(Merchant.is_active.is_(True))
        .options(selectinload(Merchant.aliases))
    )
    merchants = (await db.execute(stmt)).scalars().all()

    index: dict[str, _AliasEntry] = {}
    for m in merchants:
        ref = MerchantRef(id=m.id, slug=m.slug, name=m.name)
        for key in {normalize_query(m.slug), normalize_query(m.name)}:
            if key:
                index[key] = _AliasEntry(merchant=ref, weight=1.0)
        for alias in m.aliases:
            akey = normalize_query(alias.alias)
            if akey:
                index[akey] = _AliasEntry(merchant=ref, weight=float(alias.weight))
    return index


async def get_alias_index(db: AsyncSession, *, force: bool = False) -> dict[str, _AliasEntry]:
    global _alias_index, _alias_index_built_at
    now = time.time()
    if force or not _alias_index or (now - _alias_index_built_at) > _CACHE_TTL:
        _alias_index = await _build_alias_index(db)
        _alias_index_built_at = now
    return _alias_index


async def resolve_merchant(db: AsyncSession, query: str) -> tuple[MerchantRef | None, float]:
    """Return the best-matching merchant for a query and a confidence score.

    Strategy:
      1. Exact alias hit on the whole normalized query or any token.
      2. Fuzzy match each token against alias keys; keep the best above threshold.
    """
    index = await get_alias_index(db)
    if not index:
        return None, 0.0

    normalized = normalize_query(query)

    # 1) exact: whole query, then token-by-token (longer phrases first)
    if normalized in index:
        entry = index[normalized]
        return entry.merchant, entry.weight

    tokens = tokenize(query)
    for tok in tokens:
        if tok in index:
            entry = index[tok]
            return entry.merchant, entry.weight

    # 2) fuzzy: best similarity across alias keys vs each token
    best_ref: MerchantRef | None = None
    best_score = 0.0
    candidate_tokens = tokens or [normalized]
    for key, entry in index.items():
        for tok in candidate_tokens:
            if abs(len(tok) - len(key)) > 3:
                continue
            score = similarity(tok, key) * float(entry.weight)
            if score > best_score:
                best_score = score
                best_ref = entry.merchant

    if best_ref and best_score >= _FUZZY_THRESHOLD:
        return best_ref, round(best_score, 3)
    return None, 0.0


async def resolve_merchant_by_slug(db: AsyncSession, slug: str) -> MerchantRef | None:
    stmt = select(Merchant).where(Merchant.slug == slug)
    m = (await db.execute(stmt)).scalar_one_or_none()
    return MerchantRef(id=m.id, slug=m.slug, name=m.name) if m else None
