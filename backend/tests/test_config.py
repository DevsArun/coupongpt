"""Tests for fail-fast production configuration validation.

Requires pydantic-settings; skipped if unavailable.
"""
from __future__ import annotations

import pytest

pytest.importorskip("pydantic_settings")

from app.core.config import Settings  # noqa: E402

SECURE = "a-very-strong-secret-value-1234567890"


def _prod(**overrides):
    base = dict(
        app_env="production",
        app_debug=False,
        app_secret_key=SECURE,
        jwt_secret=SECURE,
        meili_master_key=SECURE,
        cors_origins="https://app.example.com",
    )
    base.update(overrides)
    return Settings(**base)


def test_secure_production_config_has_no_problems():
    assert _prod().production_problems() == []


def test_insecure_secret_flagged():
    problems = _prod(jwt_secret="change-me-jwt-secret").production_problems()
    assert any("JWT_SECRET" in p for p in problems)


def test_debug_flagged_in_production():
    assert any("APP_DEBUG" in p for p in _prod(app_debug=True).production_problems())


def test_wildcard_cors_flagged():
    assert any("CORS_ORIGINS" in p for p in _prod(cors_origins="*").production_problems())


def test_validate_raises_in_production_when_insecure():
    with pytest.raises(RuntimeError):
        _prod(jwt_secret="change-me-jwt-secret").validate_production()


def test_validate_noop_in_development():
    # Development never raises regardless of secrets.
    Settings(app_env="development", jwt_secret="change-me-jwt-secret").validate_production()
