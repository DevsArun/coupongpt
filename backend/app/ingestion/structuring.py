"""AI structuring stage — turn a candidate text block into a StructuredCoupon.

Tries the AI provider fallback chain first (better recall on messy text); on any
failure it degrades gracefully to the deterministic regex extractor so ingestion
never stalls because of an AI outage.
"""
from __future__ import annotations

from datetime import datetime

from app.ai.prompts import COUPON_STRUCTURING_SYSTEM, COUPON_STRUCTURING_USER
from app.ai.router import get_router
from app.core.logging import get_logger
from app.ingestion.extraction import StructuredCoupon, extract_coupon

logger = get_logger("ingestion.structuring")

_VALID_TYPES = {"percentage", "fixed", "bogo", "free_shipping", "trial", "other"}


def _parse_iso(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


async def structure_coupon(
    text: str, *, merchant_name: str, url: str | None = None, use_ai: bool = True
) -> StructuredCoupon | None:
    """Return a StructuredCoupon, or None if the text is clearly not a coupon."""
    fallback = extract_coupon(text, url=url)

    if not use_ai or not get_router().available_providers():
        return fallback

    user_prompt = COUPON_STRUCTURING_USER.format(merchant=merchant_name, raw_text=text[:3000])
    try:
        completion = await get_router().complete_json(
            COUPON_STRUCTURING_SYSTEM, user_prompt, operation="coupon_structuring"
        )
        data = completion.data
    except Exception as exc:  # noqa: BLE001 - graceful fallback
        logger.warning("ai_structuring_failed", error=str(exc))
        return fallback

    confidence = float(data.get("confidence", 0) or 0)
    if confidence <= 0:
        return None  # AI judged this not a coupon

    dtype = data.get("discount_type", "other")
    if dtype not in _VALID_TYPES:
        dtype = "other"

    return StructuredCoupon(
        title=(data.get("title") or fallback.title)[:255],
        code=(data.get("code") or None),
        discount_type=dtype,
        discount_value=data.get("discount_value"),
        currency=(data.get("currency") or None),
        expires_at=_parse_iso(data.get("expires_at")) or fallback.expires_at,
        terms=(data.get("terms") or None),
        landing_url=url,
        confidence=round(min(confidence, 1.0), 3),
        raw_text=text[:2000],
        extra={"ai_provider": completion.provider},
    )
