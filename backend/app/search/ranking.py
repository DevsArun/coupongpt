"""Multi-factor re-ranking of search candidates.

Meilisearch returns candidates ordered by textual relevance + our stored
``ranking_score``. This module performs a final in-memory blend so that
relevance, source trust, freshness, confidence, success rate, expiry, and a
duplicate penalty all contribute — never date alone. Weights are admin-tunable
via the ``ranking_weights`` setting.
"""
from __future__ import annotations

from typing import Any

DEFAULT_WEIGHTS: dict[str, float] = {
    "relevance": 0.35,
    "trust": 0.15,
    "freshness": 0.15,
    "confidence": 0.10,
    "success": 0.15,
    "expiry": 0.10,
    "duplicate_penalty": 0.20,
}


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def final_score(doc: dict[str, Any], relevance: float, weights: dict[str, float]) -> float:
    """Compute the blended score for a single candidate document."""
    score = (
        weights["relevance"] * relevance
        + weights["trust"] * _f(doc.get("source_trust_score"), 0.5)
        + weights["freshness"] * _f(doc.get("freshness_score"), 0.5)
        + weights["confidence"] * _f(doc.get("confidence_score"), 0.5)
        + weights["success"] * _f(doc.get("success_rate_score"), 0.5)
        + weights["expiry"] * _f(doc.get("expiry_score"), 0.5)
        - weights["duplicate_penalty"] * _f(doc.get("duplicate_score"), 0.0)
    )
    # Normalize into [0,1] by the sum of positive weights.
    positive = (
        weights["relevance"]
        + weights["trust"]
        + weights["freshness"]
        + weights["confidence"]
        + weights["success"]
        + weights["expiry"]
    )
    return max(0.0, min(1.0, score / positive if positive else score))


def rerank(
    hits: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return hits sorted by the blended score (desc).

    Each hit is expected to carry a ``_rankingScore`` (Meili relevance in [0,1]).
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    for hit in hits:
        relevance = _f(hit.get("_rankingScore"), 0.5)
        hit["_relevance"] = relevance
        hit["_final_score"] = final_score(hit, relevance, w)
    return sorted(hits, key=lambda h: h["_final_score"], reverse=True)
