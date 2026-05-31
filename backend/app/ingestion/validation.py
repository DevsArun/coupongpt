"""Validation engine — computes the six component scores for a coupon.

Each function is pure (no DB / IO) and returns a value in ``[0, 1]`` so the unit
tests can assert exact behaviour. The orchestration layer gathers the inputs
(source trust, duplicate counts, feedback counts) and calls these.

Scores
------
- source_trust_score : how trustworthy the origin is.
- freshness_score    : how recently the coupon was seen/updated (exp decay).
- confidence_score   : how confident extraction was that this is a real coupon.
- duplicate_score    : penalty in [0,1]; higher = more duplicative.
- success_rate_score : Wilson-smoothed success ratio from user feedback.
- expiry_score       : time-to-expiry desirability (expired = 0).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def source_trust_score(source_trust: float | None, merchant_trust: float | None) -> float:
    """Blend the source's and merchant's trust; favour the more specific source."""
    s = source_trust if source_trust is not None else None
    m = merchant_trust if merchant_trust is not None else 0.5
    if s is None:
        return _clamp(m)
    return _clamp(0.6 * s + 0.4 * m)


def freshness_score(last_seen: datetime | None, *, half_life_days: float = 21.0) -> float:
    """Exponential decay: a coupon seen today ~1.0, one half-life old ~0.5."""
    if last_seen is None:
        return 0.5
    age_days = max((_utcnow() - _aware(last_seen)).total_seconds() / 86400.0, 0.0)
    return _clamp(math.pow(0.5, age_days / half_life_days))


def confidence_score(
    *,
    has_code: bool,
    has_discount_value: bool,
    merchant_known: bool,
    ai_confidence: float | None = None,
) -> float:
    """Heuristic confidence, overridden/boosted by AI confidence when present."""
    base = 0.3
    if merchant_known:
        base += 0.25
    if has_discount_value:
        base += 0.2
    if has_code:
        base += 0.15
    heuristic = _clamp(base)
    if ai_confidence is None:
        return heuristic
    # Weighted blend toward AI when it is confident.
    return _clamp(0.5 * heuristic + 0.5 * _clamp(ai_confidence))


def duplicate_score(duplicate_count: int) -> float:
    """0 duplicates -> 0 penalty; saturates toward 1 as duplicates grow."""
    if duplicate_count <= 0:
        return 0.0
    return _clamp(1.0 - math.pow(0.5, duplicate_count))


def success_rate_score(success_reports: int, fail_reports: int) -> float:
    """Wilson lower bound of the success proportion (smooths small samples)."""
    n = success_reports + fail_reports
    if n == 0:
        return 0.5  # neutral prior
    z = 1.96
    phat = success_reports / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return _clamp((centre - margin) / denom)


def expiry_score(expires_at: datetime | None, *, sweet_spot_days: float = 14.0) -> float:
    """Desirability based on time-to-expiry.

    - Expired           -> 0.0
    - No expiry (evergreen) -> 0.7 (good but slightly uncertain)
    - Plenty of runway  -> ~1.0, easing down as it approaches expiry.
    """
    if expires_at is None:
        return 0.7
    days_left = (_aware(expires_at) - _utcnow()).total_seconds() / 86400.0
    if days_left <= 0:
        return 0.0
    if days_left >= sweet_spot_days:
        return 1.0
    # Linear ramp from 0.3 (about to expire) to 1.0 (>= sweet spot).
    return _clamp(0.3 + 0.7 * (days_left / sweet_spot_days))


def all_scores(
    *,
    source_trust: float | None,
    merchant_trust: float | None,
    last_seen: datetime | None,
    has_code: bool,
    has_discount_value: bool,
    merchant_known: bool,
    ai_confidence: float | None,
    duplicate_count: int,
    success_reports: int,
    fail_reports: int,
    expires_at: datetime | None,
) -> dict[str, float]:
    """Compute all six component scores at once."""
    return {
        "source_trust_score": round(source_trust_score(source_trust, merchant_trust), 3),
        "freshness_score": round(freshness_score(last_seen), 3),
        "confidence_score": round(
            confidence_score(
                has_code=has_code,
                has_discount_value=has_discount_value,
                merchant_known=merchant_known,
                ai_confidence=ai_confidence,
            ),
            3,
        ),
        "duplicate_score": round(duplicate_score(duplicate_count), 3),
        "success_rate_score": round(success_rate_score(success_reports, fail_reports), 3),
        "expiry_score": round(expiry_score(expires_at), 3),
    }
