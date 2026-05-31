"""Blend the six component scores into a single ranking score.

This mirrors ``app.search.ranking`` but operates on the *stored* component scores
(no query-time relevance term, since this runs at ingest/validation time). The
search path later combines this stored ``ranking_score`` with live relevance.
"""
from __future__ import annotations

# Static-context weights (no relevance term). Sums to 1.0 minus duplicate penalty.
STORED_WEIGHTS: dict[str, float] = {
    "trust": 0.25,
    "freshness": 0.20,
    "confidence": 0.15,
    "success": 0.25,
    "expiry": 0.15,
    "duplicate_penalty": 0.30,
}


def compute_ranking_score(scores: dict[str, float], weights: dict[str, float] | None = None) -> float:
    w = {**STORED_WEIGHTS, **(weights or {})}
    positive = w["trust"] + w["freshness"] + w["confidence"] + w["success"] + w["expiry"]
    raw = (
        w["trust"] * scores.get("source_trust_score", 0.5)
        + w["freshness"] * scores.get("freshness_score", 0.5)
        + w["confidence"] * scores.get("confidence_score", 0.5)
        + w["success"] * scores.get("success_rate_score", 0.5)
        + w["expiry"] * scores.get("expiry_score", 0.5)
        - w["duplicate_penalty"] * scores.get("duplicate_score", 0.0)
    )
    normalized = raw / positive if positive else raw
    return round(max(0.0, min(1.0, normalized)), 4)
