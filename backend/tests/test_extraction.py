"""Tests for the deterministic coupon extraction stage."""
from __future__ import annotations

from app.ingestion import extraction


def test_extract_percentage_and_code():
    sc = extraction.extract_coupon("Get 30% off with code SAVE30 at checkout")
    assert sc.discount_type == "percentage"
    assert sc.discount_value == 30.0
    assert sc.code == "SAVE30"
    assert sc.confidence > 0.5


def test_extract_fixed_amount_currency():
    sc = extraction.extract_coupon("Take $15 off your first order. Use code NEW15")
    assert sc.discount_type == "fixed"
    assert sc.discount_value == 15.0
    assert sc.currency == "USD"
    assert sc.code == "NEW15"


def test_extract_free_shipping():
    sc = extraction.extract_coupon("Enjoy free shipping on all orders this weekend")
    assert sc.discount_type == "free_shipping"


def test_extract_bogo():
    sc = extraction.extract_coupon("Buy one get one free on selected items")
    assert sc.discount_type == "bogo"


def test_extract_date():
    sc = extraction.extract_coupon("50% off, expires 2026-12-31, code HALF")
    assert sc.expires_at is not None
    assert sc.expires_at.year == 2026


def test_looks_like_coupon_positive():
    assert extraction.looks_like_coupon("20% off with code ABC123")


def test_looks_like_coupon_negative():
    assert not extraction.looks_like_coupon("Welcome to our homepage about our company")
