"""Extraction stage — deterministic regex extraction of coupon attributes.

This is the AI-free baseline. It produces a :class:`StructuredCoupon` from text
and is also used as the graceful fallback when the AI structuring step fails.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

# CODE: uppercase alphanumeric tokens, often near the word "code".
_CODE_NEAR_RE = re.compile(
    r"(?:code|coupon|promo|voucher)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{2,19})", re.IGNORECASE
)
_CODE_STANDALONE_RE = re.compile(r"\b([A-Z0-9]{4,15})\b")
_PERCENT_RE = re.compile(r"(\d{1,3})\s*%\s*(?:off|discount)?", re.IGNORECASE)
_FIXED_RE = re.compile(r"(?:[\$₹€£]|usd|inr|eur|gbp)\s*(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
_FREE_SHIP_RE = re.compile(r"free\s+(?:shipping|delivery)", re.IGNORECASE)
_BOGO_RE = re.compile(r"\b(bogo|buy\s+one\s+get\s+one)\b", re.IGNORECASE)
_TRIAL_RE = re.compile(r"\bfree\s+trial\b|\b\d+\s*-?\s*day\s+trial\b", re.IGNORECASE)

_DATE_PATTERNS = [
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),                       # 2026-02-14
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),                   # 14/02/2026
]

_CURRENCY_MAP = {"$": "USD", "₹": "INR", "€": "EUR", "£": "GBP"}


@dataclass
class StructuredCoupon:
    title: str
    code: str | None = None
    discount_type: str = "other"
    discount_value: float | None = None
    currency: str | None = None
    expires_at: datetime | None = None
    terms: str | None = None
    landing_url: str | None = None
    confidence: float = 0.4
    raw_text: str = ""
    extra: dict = field(default_factory=dict)


def _parse_date(text: str) -> datetime | None:
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        try:
            if pat.pattern.startswith(r"\b(\d{4})"):
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return datetime(y, mo, d)
        except ValueError:
            continue
    return None


def extract_code(text: str) -> str | None:
    m = _CODE_NEAR_RE.search(text)
    if m:
        return m.group(1).upper()
    return None


def extract_discount(text: str) -> tuple[str, float | None, str | None]:
    if _FREE_SHIP_RE.search(text):
        return "free_shipping", None, None
    if _TRIAL_RE.search(text):
        return "trial", None, None
    if _BOGO_RE.search(text):
        return "bogo", None, None
    m = _PERCENT_RE.search(text)
    if m:
        return "percentage", float(m.group(1)), None
    m = _FIXED_RE.search(text)
    if m:
        currency = None
        for sym, code in _CURRENCY_MAP.items():
            if sym in text:
                currency = code
                break
        return "fixed", float(m.group(1)), currency
    return "other", None, None


def extract_coupon(text: str, *, title_hint: str | None = None, url: str | None = None) -> StructuredCoupon:
    text = text.strip()
    code = extract_code(text)
    dtype, dvalue, currency = extract_discount(text)
    expires = _parse_date(text)

    title = title_hint or text.split("\n", 1)[0][:120] or "Coupon"

    # Heuristic confidence: stronger signal => higher confidence.
    confidence = 0.3
    if dtype != "other":
        confidence += 0.25
    if code:
        confidence += 0.2
    if expires:
        confidence += 0.1
    confidence = min(confidence, 0.85)

    return StructuredCoupon(
        title=title.strip(),
        code=code,
        discount_type=dtype,
        discount_value=dvalue,
        currency=currency,
        expires_at=expires,
        terms=None,
        landing_url=url,
        confidence=round(confidence, 3),
        raw_text=text[:2000],
    )


def looks_like_coupon(text: str) -> bool:
    """Quick gate: does this block plausibly describe a coupon/offer?"""
    if not text:
        return False
    signals = (
        _PERCENT_RE.search(text)
        or _FIXED_RE.search(text)
        or _FREE_SHIP_RE.search(text)
        or _BOGO_RE.search(text)
        or _TRIAL_RE.search(text)
        or _CODE_NEAR_RE.search(text)
    )
    return bool(signals)
