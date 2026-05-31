"""Tests for AI provider base helpers (JSON extraction from model output)."""
from __future__ import annotations

import pytest

from app.ai.base import AIError, AIProvider


def test_extract_plain_json():
    assert AIProvider._extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    text = "```json\n{\"merchant\": \"nike\", \"confidence\": 0.9}\n```"
    out = AIProvider._extract_json(text)
    assert out["merchant"] == "nike"


def test_extract_json_with_prose():
    text = 'Here is the result: {"x": true} hope that helps!'
    assert AIProvider._extract_json(text) == {"x": True}


def test_extract_invalid_raises():
    with pytest.raises(AIError):
        AIProvider._extract_json("no json here at all")
