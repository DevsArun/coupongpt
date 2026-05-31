"""Unit tests for the six-factor validation scoring engine (pure functions)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.ingestion import validation as v


def _now():
    return datetime.now(timezone.utc)


def test_scores_are_bounded_0_1():
    scores = v.all_scores(
        source_trust=0.9, merchant_trust=0.9, last_seen=_now(), has_code=True,
        has_discount_value=True, merchant_known=True, ai_confidence=0.8,
        duplicate_count=0, success_reports=5, fail_reports=1,
        expires_at=_now() + timedelta(days=20),
    )
    for key, value in scores.items():
        assert 0.0 <= value <= 1.0, f"{key}={value} out of range"


def test_freshness_decays_with_age():
    fresh = v.freshness_score(_now())
    old = v.freshness_score(_now() - timedelta(days=42))
    assert fresh > old
    assert fresh > 0.9
    assert old < 0.3


def test_freshness_none_is_neutral():
    assert v.freshness_score(None) == 0.5


def test_expiry_expired_is_zero():
    assert v.expiry_score(_now() - timedelta(days=1)) == 0.0


def test_expiry_far_future_is_high():
    assert v.expiry_score(_now() + timedelta(days=60)) == 1.0


def test_expiry_none_is_evergreen():
    assert v.expiry_score(None) == 0.7


def test_duplicate_penalty_monotonic():
    assert v.duplicate_score(0) == 0.0
    assert v.duplicate_score(1) < v.duplicate_score(3)
    assert v.duplicate_score(10) <= 1.0


def test_success_rate_neutral_without_feedback():
    assert v.success_rate_score(0, 0) == 0.5


def test_success_rate_high_with_many_successes():
    high = v.success_rate_score(50, 1)
    low = v.success_rate_score(1, 50)
    assert high > 0.7
    assert low < 0.2
    assert high > low


def test_confidence_boosted_by_signals():
    weak = v.confidence_score(has_code=False, has_discount_value=False, merchant_known=False)
    strong = v.confidence_score(has_code=True, has_discount_value=True, merchant_known=True)
    assert strong > weak


def test_confidence_blends_ai():
    blended = v.confidence_score(
        has_code=True, has_discount_value=True, merchant_known=True, ai_confidence=0.95
    )
    assert 0.0 <= blended <= 1.0


def test_source_trust_blend_prefers_source():
    blended = v.source_trust_score(0.9, 0.5)
    assert 0.5 < blended < 0.9
