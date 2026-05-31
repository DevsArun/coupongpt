"""Tests for the stored ranking-score blend (never rank by one factor alone)."""
from __future__ import annotations

from app.ingestion import scoring


def _scores(**overrides):
    base = {
        "source_trust_score": 0.5,
        "freshness_score": 0.5,
        "confidence_score": 0.5,
        "success_rate_score": 0.5,
        "expiry_score": 0.5,
        "duplicate_score": 0.0,
    }
    base.update(overrides)
    return base


def test_ranking_in_range():
    assert 0.0 <= scoring.compute_ranking_score(_scores()) <= 1.0


def test_high_quality_beats_low_quality():
    great = scoring.compute_ranking_score(
        _scores(source_trust_score=0.95, freshness_score=1.0, confidence_score=0.9,
                success_rate_score=0.9, expiry_score=1.0)
    )
    weak = scoring.compute_ranking_score(
        _scores(source_trust_score=0.3, freshness_score=0.1, confidence_score=0.2,
                success_rate_score=0.1, expiry_score=0.2, duplicate_score=0.8)
    )
    assert great > weak
    assert great > 0.8


def test_duplicate_penalty_lowers_score():
    no_dup = scoring.compute_ranking_score(_scores(duplicate_score=0.0))
    with_dup = scoring.compute_ranking_score(_scores(duplicate_score=0.9))
    assert with_dup < no_dup


def test_not_ranked_by_freshness_alone():
    # A very fresh but otherwise poor coupon must not outrank a strong stale one.
    fresh_poor = scoring.compute_ranking_score(
        _scores(freshness_score=1.0, source_trust_score=0.2, confidence_score=0.2,
                success_rate_score=0.1, expiry_score=0.2)
    )
    stale_strong = scoring.compute_ranking_score(
        _scores(freshness_score=0.2, source_trust_score=0.95, confidence_score=0.9,
                success_rate_score=0.9, expiry_score=0.9)
    )
    assert stale_strong > fresh_poor
