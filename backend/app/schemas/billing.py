"""Billing schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    description: str | None
    price_cents: int
    currency: str
    billing_period: str
    quota_limit: int
    quota_window: str
    sort_order: int


class CheckoutIn(BaseModel):
    plan_slug: str
    gateway: str = Field(default="stripe", description="stripe|razorpay")


class CancelIn(BaseModel):
    at_period_end: bool = True


class ChangePlanIn(BaseModel):
    plan_slug: str
    gateway: str = "stripe"


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    amount_cents: int
    currency: str
    status: str
    issued_at: datetime | None
    paid_at: datetime | None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount_cents: int
    currency: str
    status: str
    gateway: str
    paid_at: datetime | None
    created_at: datetime
