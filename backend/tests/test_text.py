"""Tests for text normalization, fuzzy matching, and hashing utilities."""
from __future__ import annotations

from app.utils import text


def test_normalize_lowercases_and_strips_punctuation():
    assert text.normalize_query("  BST  niek!! coupn ") == "bst niek coupn"


def test_normalize_strips_accents():
    assert text.normalize_query("Café Déjà") == "cafe deja"


def test_tokenize():
    assert text.tokenize("best nike offer feb") == ["best", "nike", "offer", "feb"]


def test_levenshtein_transposition_is_one():
    # "niek" -> "nike" is an adjacent transposition (Damerau distance 1).
    assert text.levenshtein("niek", "nike") == 1


def test_similarity_catches_common_typos():
    assert text.similarity("niek", "nike") >= 0.74
    assert text.similarity("amazn", "amazon") > 0.8
    assert text.similarity("hostingr", "hostinger") > 0.85


def test_similarity_identical_is_one():
    assert text.similarity("nike", "nike") == 1.0


def test_content_hash_is_stable_and_order_sensitive():
    h1 = text.content_hash("2", "NIKE25", "fixed", "25", "nike 25 off")
    h2 = text.content_hash("2", "NIKE25", "fixed", "25", "nike 25 off")
    h3 = text.content_hash("2", "OTHER", "fixed", "25", "nike 25 off")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_slugify():
    assert text.slugify("Web Hosting!") == "web-hosting"
