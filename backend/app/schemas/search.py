"""Search request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DiscountIntent(BaseModel):
    type: str = "any"  # percentage|fixed|free_shipping|bogo|trial|any
    min_value: float | None = None


class QueryIntent(BaseModel):
    raw_query: str
    corrected_query: str
    merchant: str | None = None
    merchant_id: int | None = None
    discount_intent: DiscountIntent | None = None
    time_intent: str | None = None  # today|this_week|this_month|this_year|expiring_soon
    keywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = "heuristic"  # heuristic | ai:<provider>


class CouponResult(BaseModel):
    id: int
    uuid: str
    title: str
    code: str | None = None
    description: str | None = None
    merchant_id: int
    merchant_name: str
    merchant_slug: str
    discount_type: str
    discount_value: float | None = None
    currency: str | None = None
    landing_url: str | None = None
    expires_at: str | None = None
    ranking_score: float = 0.0
    relevance: float = 0.0
    has_code: bool = False


class SearchResponse(BaseModel):
    intent: QueryIntent
    results: list[CouponResult]
    total: int
    latency_ms: int
    cache_hit: bool = False


class Suggestion(BaseModel):
    text: str
    type: str  # merchant | query | coupon


class SuggestResponse(BaseModel):
    suggestions: list[Suggestion]


class QuotaStatus(BaseModel):
    plan: str
    limit: int
    window: str
    used: int
    remaining: int
    resets_in_seconds: int
