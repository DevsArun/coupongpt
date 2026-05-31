"""Tests for query-time re-ranking blend (Meili relevance + stored quality)."""
from __future__ import annotations

from app.search import ranking


def test_rerank_orders_by_blended_score():
    hits = [
        {  # high raw relevance, poor quality
            "id": 1, "_rankingScore": 0.95, "source_trust_score": 0.4,
            "freshness_score": 0.2, "confidence_score": 0.3, "success_rate_score": 0.2,
            "expiry_score": 0.2, "duplicate_score": 0.6,
        },
        {  # lower relevance, excellent quality
            "id": 2, "_rankingScore": 0.7, "source_trust_score": 0.95,
            "freshness_score": 0.95, "confidence_score": 0.9, "success_rate_score": 0.9,
            "expiry_score": 0.95, "duplicate_score": 0.0,
        },
    ]
    ranked = ranking.rerank(hits)
    assert ranked[0]["id"] == 2
    assert ranked[0]["_final_score"] > ranked[1]["_final_score"]


def test_rerank_attaches_scores():
    hits = [{"id": 1, "_rankingScore": 0.5}]
    ranked = ranking.rerank(hits)
    assert "_final_score" in ranked[0]
    assert "_relevance" in ranked[0]
    assert 0.0 <= ranked[0]["_final_score"] <= 1.0


def test_rerank_empty():
    assert ranking.rerank([]) == []


def test_custom_weights_respected():
    hits = [{"id": 1, "_rankingScore": 1.0, "source_trust_score": 0.0,
             "freshness_score": 0.0, "confidence_score": 0.0, "success_rate_score": 0.0,
             "expiry_score": 0.0, "duplicate_score": 0.0}]
    # Weight everything on relevance -> score approaches 1.0
    ranked = ranking.rerank(hits, {"relevance": 1.0, "trust": 0.0, "freshness": 0.0,
                                   "confidence": 0.0, "success": 0.0, "expiry": 0.0,
                                   "duplicate_penalty": 0.0})
    assert ranked[0]["_final_score"] > 0.9
