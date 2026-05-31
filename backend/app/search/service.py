"""Search orchestration — the hot path.

    quota (caller) -> cache -> understand -> Meili query -> re-rank -> analytics

Designed to stay under ~200ms: the full response is cached per normalized query +
filters, AI understanding is cached separately, retrieval is Meilisearch's
millisecond path, and re-ranking is in-memory over a bounded candidate set.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.models.search import SearchQuery
from app.schemas.search import CouponResult, QueryIntent, SearchResponse
from app.search import client as meili
from app.search.ranking import rerank
from app.search.understanding import understand_query
from app.services import settings_service

logger = get_logger("search.service")

_CACHE_PREFIX = "search:result:"


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _cache_key(normalized: str, merchant_id: int | None, filters: list[str], limit: int) -> str:
    raw = json.dumps(
        {"q": normalized, "m": merchant_id, "f": sorted(filters), "l": limit}, sort_keys=True
    )
    return _CACHE_PREFIX + hashlib.sha256(raw.encode()).hexdigest()


def _build_filters(intent: QueryIntent) -> list[str]:
    filters: list[str] = ["status = active"]

    if intent.merchant_id is not None:
        filters.append(f"merchant_id = {intent.merchant_id}")

    # Exclude expired coupons (allow null expiry = evergreen).
    now = _now_ts()
    filters.append(f"(expires_at_ts >= {now} OR expires_at_ts IS NULL)")

    di = intent.discount_intent
    if di and di.type and di.type != "any":
        filters.append(f"discount_type = {di.type}")
        if di.min_value is not None and di.type in ("percentage", "fixed"):
            filters.append(f"discount_value >= {di.min_value}")

    if intent.time_intent == "expiring_soon":
        soon = _now_ts() + 7 * 86400
        filters.append(f"expires_at_ts <= {soon}")

    return filters


def _hit_to_result(hit: dict[str, Any]) -> CouponResult:
    return CouponResult(
        id=hit["id"],
        uuid=hit.get("uuid", ""),
        title=hit.get("title", ""),
        code=hit.get("code"),
        description=hit.get("description"),
        merchant_id=hit.get("merchant_id", 0),
        merchant_name=hit.get("merchant_name", ""),
        merchant_slug=hit.get("merchant_slug", ""),
        discount_type=hit.get("discount_type", "other"),
        discount_value=hit.get("discount_value"),
        currency=hit.get("currency"),
        landing_url=hit.get("landing_url"),
        expires_at=hit.get("expires_at"),
        ranking_score=float(hit.get("_final_score", hit.get("ranking_score", 0.0))),
        relevance=float(hit.get("_relevance", 0.0)),
        has_code=bool(hit.get("has_code")),
    )


async def search(
    db: AsyncSession,
    raw_query: str,
    *,
    user_id: int | None = None,
    limit: int = 20,
    use_ai: bool = True,
) -> SearchResponse:
    start = time.perf_counter()
    redis = get_redis()

    intent = await understand_query(db, raw_query, use_ai=use_ai)
    filters = _build_filters(intent)
    cache_key = _cache_key(intent.corrected_query, intent.merchant_id, filters, limit)

    # ---- whole-response cache ----
    try:
        cached = await redis.get(cache_key)
        if cached:
            payload = json.loads(cached)
            latency = int((time.perf_counter() - start) * 1000)
            await _record_analytics(db, raw_query, intent, payload["total"], latency, True, user_id)
            return SearchResponse(
                intent=intent,
                results=[CouponResult(**r) for r in payload["results"]],
                total=payload["total"],
                latency_ms=latency,
                cache_hit=True,
            )
    except Exception:
        pass

    # ---- retrieval ----
    search_text = intent.corrected_query or raw_query
    params = {
        "limit": max(limit * 3, limit),  # over-fetch so re-ranking has room
        "filter": filters,
        "showRankingScore": True,
        "attributesToRetrieve": ["*"],
    }
    try:
        result = await meili.raw_search(search_text, params)
        hits = result.get("hits", [])
    except Exception as exc:  # noqa: BLE001 - never 500 the search path on Meili hiccup
        logger.error("meili_search_failed", error=str(exc))
        hits = []

    weights = await settings_service.get_setting(db, "ranking_weights", None)
    ranked = rerank(hits, weights if isinstance(weights, dict) else None)[:limit]
    results = [_hit_to_result(h) for h in ranked]

    latency = int((time.perf_counter() - start) * 1000)

    # ---- cache + analytics ----
    try:
        ttl_cfg = await settings_service.get_setting(db, "search_defaults", {})
        ttl = int(ttl_cfg.get("cache_ttl_seconds", 300)) if isinstance(ttl_cfg, dict) else 300
        await redis.set(
            cache_key,
            json.dumps({"results": [r.model_dump() for r in results], "total": len(results)}),
            ex=ttl,
        )
    except Exception:
        pass

    await _record_analytics(db, raw_query, intent, len(results), latency, False, user_id)

    return SearchResponse(
        intent=intent,
        results=results,
        total=len(results),
        latency_ms=latency,
        cache_hit=False,
    )


async def _record_analytics(
    db: AsyncSession,
    raw_query: str,
    intent: QueryIntent,
    results_count: int,
    latency_ms: int,
    cache_hit: bool,
    user_id: int | None,
) -> None:
    """Persist a search analytics row. Failures must not break search."""
    try:
        row = SearchQuery(
            user_id=user_id,
            raw_query=raw_query[:512],
            normalized_query=intent.corrected_query[:512],
            detected_merchant_id=intent.merchant_id,
            intent=intent.model_dump(),
            results_count=results_count,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            ai_provider=intent.source if intent.source.startswith("ai:") else None,
        )
        db.add(row)
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("analytics_record_failed", error=str(exc))



async def suggest(db: AsyncSession, prefix: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Lightweight autocomplete: merchant names + matching coupon titles."""
    from app.services import merchant_service

    prefix_norm = prefix.strip().lower()
    suggestions: list[dict[str, str]] = []
    seen: set[str] = set()

    # Merchant suggestions from the alias index.
    if prefix_norm:
        index = await merchant_service.get_alias_index(db)
        merchant_names = {e.merchant.name for e in index.values()}
        for name in sorted(merchant_names):
            if name.lower().startswith(prefix_norm) and name not in seen:
                suggestions.append({"text": f"{name} coupons", "type": "merchant"})
                seen.add(name)
            if len(suggestions) >= limit // 2:
                break

    # Coupon-title suggestions from Meilisearch.
    try:
        result = await meili.raw_search(
            prefix,
            {"limit": limit, "attributesToRetrieve": ["title", "merchant_name"], "filter": ["status = active"]},
        )
        for hit in result.get("hits", []):
            title = hit.get("title", "")
            if title and title not in seen:
                suggestions.append({"text": title, "type": "coupon"})
                seen.add(title)
            if len(suggestions) >= limit:
                break
    except Exception:
        pass

    return suggestions[:limit]
