"""Security tests: password hashing and JWT issue/verify.

Requires bcrypt, PyJWT, and pydantic-settings; skipped if unavailable.
"""
from __future__ import annotations

import pytest

pytest.importorskip("bcrypt")
pytest.importorskip("jwt")
pytest.importorskip("pydantic_settings")

from app.core import security  # noqa: E402


def test_password_hash_roundtrip():
    h = security.hash_password("S3cretpass!")
    assert h != "S3cretpass!"
    assert security.verify_password("S3cretpass!", h)
    assert not security.verify_password("wrong", h)


def test_password_hashes_are_salted():
    assert security.hash_password("same") != security.hash_password("same")


def test_access_token_roundtrip():
    token = security.create_access_token(42, role="user", permissions=["coupons.read"])
    payload = security.decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert payload["role"] == "user"
    assert "coupons.read" in payload["perms"]


def test_invalid_token_rejected():
    import jwt

    with pytest.raises(jwt.PyJWTError):
        security.decode_token("not.a.valid.token")


def test_refresh_token_hashing_is_deterministic():
    raw = security.generate_refresh_token()
    assert security.hash_token(raw) == security.hash_token(raw)
    assert len(security.hash_token(raw)) == 64


def test_referral_code_format():
    code = security.generate_referral_code()
    assert len(code) == 8
    assert code.isalnum()
