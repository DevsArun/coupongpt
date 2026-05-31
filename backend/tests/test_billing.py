"""Billing logic tests: period calculation and gateway demo-mode behavior.

Requires SQLAlchemy + structlog (imported transitively); skipped if absent.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("structlog")


def test_period_end_by_billing_period():
    from app.services import billing_service

    start = datetime(2026, 1, 1)
    month = billing_service._period_end(SimpleNamespace(billing_period="month"), start)
    year = billing_service._period_end(SimpleNamespace(billing_period="year"), start)
    day = billing_service._period_end(SimpleNamespace(billing_period="day"), start)
    life = billing_service._period_end(SimpleNamespace(billing_period="lifetime"), start)
    assert (month - start).days == 30
    assert (year - start).days == 365
    assert (day - start).days == 1
    assert (life - start).days > 3000


def test_stripe_demo_mode_when_unconfigured():
    from app.billing.stripe_gateway import StripeGateway

    gw = StripeGateway(api_key="")  # not configured
    plan = SimpleNamespace(stripe_price_id=None, slug="pro", billing_period="month")
    user = SimpleNamespace(id=1, email="a@b.c")
    result = asyncio.run(gw.create_checkout(plan=plan, user=user, success_url="s", cancel_url="c"))
    assert result.mode == "demo"


def test_razorpay_demo_mode_when_unconfigured():
    from app.billing.razorpay_gateway import RazorpayGateway

    gw = RazorpayGateway(api_key="", secret="")
    plan = SimpleNamespace(razorpay_plan_id=None, slug="pro", billing_period="month")
    user = SimpleNamespace(id=1, email="a@b.c")
    result = asyncio.run(gw.create_checkout(plan=plan, user=user, success_url="s", cancel_url="c"))
    assert result.mode == "demo"
