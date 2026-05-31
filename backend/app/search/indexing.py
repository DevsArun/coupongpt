"""Coupon -> Meilisearch document mapping and (re)index helpers.

A single source of truth for the document shape keeps the indexer (Phase 5) and
the search service (Phase 4) in agreement on field names.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.catalog import Merchant
from app.models.coupon import Coupon


def _ts(dt: datetime | None) -> int | None:
    return int(dt.timestamp()) if dt else None


def coupon_to_document(
    coupon: Coupon,
    merchant: Merchant,
    *,
    merchant_aliases: list[str] | None = None,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Map a coupon ORM row to a flat Meilisearch document."""
    return {
        "id": coupon.id,
        "uuid": coupon.uuid,
        "title": coupon.title,
        "description": coupon.description,
        "code": coupon.code,
        "has_code": bool(coupon.code),
        "merchant_id": coupon.merchant_id,
        "merchant_slug": merchant.slug,
        "merchant_name": merchant.name,
        "merchant_aliases": merchant_aliases or [],
        "categories": categories or [],
        "discount_type": coupon.discount_type,
        "discount_value": float(coupon.discount_value) if coupon.discount_value is not None else None,
        "currency": coupon.currency,
        "landing_url": coupon.landing_url,
        "status": coupon.status,
        "starts_at_ts": _ts(coupon.starts_at),
        "expires_at_ts": _ts(coupon.expires_at),
        "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
        "created_at_ts": _ts(coupon.created_at),
        # component + blended scores used by re-ranking
        "source_trust_score": float(coupon.source_trust_score),
        "freshness_score": float(coupon.freshness_score),
        "confidence_score": float(coupon.confidence_score),
        "duplicate_score": float(coupon.duplicate_score),
        "success_rate_score": float(coupon.success_rate_score),
        "expiry_score": float(coupon.expiry_score),
        "ranking_score": float(coupon.ranking_score),
    }
