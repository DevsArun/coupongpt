"""Query understanding: turn a raw query into structured search intent.

Pipeline:
  1. Normalize the query.
  2. Heuristic pass — detect time intent, discount intent, and a candidate
     merchant via the alias index (handles typos like "niek" -> nike).
  3. AI pass (optional, feature-flagged) — call the provider fallback chain to
     get a corrected query, merchant, keywords, and confidence.
  4. Merge — prefer the AI result when confident, but always reconcile the
     detected merchant against our catalog so we never filter on an unknown id.

The AI pass is cached in Redis keyed by the normalized query so repeated queries
do not re-invoke the model — this is what keeps the hot path under budget.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import QUERY_UNDERSTANDING_SYSTEM, QUERY_UNDERSTANDING_USER
from app.ai.router import get_router
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.schemas.search import DiscountIntent, QueryIntent
from app.services import merchant_service
from app.utils.text import normalize_query, tokenize

logger = get_logger("search.understanding")

_AI_CACHE_PREFIX = "ai:qu:"
_AI_CACHE_TTL = 86400  # 1 day — query understanding is stable per query

_TIME_PATTERNS: list[tuple[str, str]] = [
    (r"\b(today|now|tonight)\b", "today"),
    (r"\b(this\s+week|weekly)\b", "this_week"),
    (r"\b(this\s+month|monthly|january|february|march|april|may|june|july|august|"
     r"september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b",
     "this_month"),
    (r"\b(this\s+year|yearly|annual)\b", "this_year"),
    (r"\b(expiring|ending|last\s+chance|soon)\b", "expiring_soon"),
]

_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")
_FIXED_RE = re.compile(r"[\$₹€£]\s*(\d+(?:\.\d+)?)")


def _heuristic_time_intent(normalized: str) -> str | None:
    for pattern, label in _TIME_PATTERNS:
        if re.search(pattern, normalized):
            return label
    return None


def _heuristic_discount_intent(normalized: str) -> DiscountIntent | None:
    if "free shipping" in normalized or "free delivery" in normalized:
        return DiscountIntent(type="free_shipping")
    if "bogo" in normalized or "buy one" in normalized:
        return DiscountIntent(type="bogo")
    if "trial" in normalized or "free trial" in normalized:
        return DiscountIntent(type="trial")
    m = _PERCENT_RE.search(normalized)
    if m:
        return DiscountIntent(type="percentage", min_value=float(m.group(1)))
    m = _FIXED_RE.search(normalized)
    if m:
        return DiscountIntent(type="fixed", min_value=float(m.group(1)))
    if any(w in normalized for w in ("discount", "off", "deal", "sale", "offer", "coupon")):
        return DiscountIntent(type="any")
    return None


_STOPWORDS = {
    "best", "coupon", "coupons", "code", "codes", "promo", "deal", "deals",
    "offer", "offers", "discount", "discounts", "today", "now", "the", "a", "an",
    "for", "off", "sale", "voucher", "save", "savings",
}


def _keywords(normalized: str, merchant_slug: str | None) -> list[str]:
    toks = tokenize(normalized)
    return [t for t in toks if t not in _STOPWORDS and t != merchant_slug]


async def _ai_understand(query: str, merchant_hints: list[str]) -> dict | None:
    """Call the AI fallback chain, with Redis caching. Returns parsed dict or None."""
    normalized = normalize_query(query)
    cache_key = f"{_AI_CACHE_PREFIX}{normalized}"
    redis = get_redis()
    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # cache is best-effort

    router = get_router()
    if not router.available_providers():
        return None

    user_prompt = QUERY_UNDERSTANDING_USER.format(
        query=query, merchant_hints=", ".join(merchant_hints[:25]) or "(none)"
    )
    try:
        completion = await router.complete_json(
            QUERY_UNDERSTANDING_SYSTEM, user_prompt, operation="query_understanding"
        )
    except Exception as exc:  # noqa: BLE001 - graceful degradation to heuristics
        logger.warning("ai_understanding_failed", error=str(exc))
        return None

    data = completion.data
    data["_provider"] = completion.provider
    try:
        await redis.set(cache_key, json.dumps(data), ex=_AI_CACHE_TTL)
    except Exception:
        pass
    return data


async def understand_query(db: AsyncSession, raw_query: str, *, use_ai: bool = True) -> QueryIntent:
    normalized = normalize_query(raw_query)

    # ---- Heuristic baseline ----
    time_intent = _heuristic_time_intent(normalized)
    discount_intent = _heuristic_discount_intent(normalized)
    merchant_ref, merchant_conf = await merchant_service.resolve_merchant(db, raw_query)
    merchant_slug = merchant_ref.slug if merchant_ref else None

    intent = QueryIntent(
        raw_query=raw_query,
        corrected_query=normalized,
        merchant=merchant_slug,
        merchant_id=merchant_ref.id if merchant_ref else None,
        discount_intent=discount_intent,
        time_intent=time_intent,
        keywords=_keywords(normalized, merchant_slug),
        confidence=round(0.4 + 0.5 * merchant_conf, 3),
        source="heuristic",
    )

    if not use_ai:
        return intent

    # ---- AI enrichment ----
    index = await merchant_service.get_alias_index(db)
    hints = sorted({e.merchant.slug for e in index.values()})
    ai = await _ai_understand(raw_query, hints)
    if not ai:
        return intent

    corrected = (ai.get("corrected_query") or "").strip() or intent.corrected_query
    ai_merchant = (ai.get("merchant") or "").strip().lower() or None

    # Reconcile AI's merchant guess against our catalog.
    resolved_id = intent.merchant_id
    resolved_slug = intent.merchant
    if ai_merchant:
        ref, conf = await merchant_service.resolve_merchant(db, ai_merchant)
        if ref:
            resolved_id, resolved_slug = ref.id, ref.slug

    discount = intent.discount_intent
    ai_discount = ai.get("discount_intent")
    if isinstance(ai_discount, dict):
        discount = DiscountIntent(
            type=ai_discount.get("type", "any") or "any",
            min_value=ai_discount.get("min_value"),
        )

    return QueryIntent(
        raw_query=raw_query,
        corrected_query=corrected,
        merchant=resolved_slug,
        merchant_id=resolved_id,
        discount_intent=discount,
        time_intent=ai.get("time_intent") or intent.time_intent,
        keywords=ai.get("keywords") or intent.keywords,
        confidence=float(ai.get("confidence", intent.confidence) or intent.confidence),
        source=f"ai:{ai.get('_provider', 'unknown')}",
    )
