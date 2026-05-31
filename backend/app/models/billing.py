"""Billing models: plans, subscriptions, payment methods, payments, invoices, webhooks."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, PKMixin, TimestampMixin

BILLING_PERIODS = ("day", "month", "year", "lifetime", "custom")
QUOTA_WINDOWS = ("day", "month")
GATEWAYS = ("stripe", "razorpay", "manual")
SUB_STATUS = ("trialing", "active", "past_due", "canceled", "expired", "paused")
PAYMENT_STATUS = ("pending", "succeeded", "failed", "refunded", "partially_refunded")
INVOICE_STATUS = ("draft", "open", "paid", "void", "uncollectible")
WEBHOOK_STATUS = ("received", "processed", "failed", "ignored")


class Plan(PKMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), default="USD", nullable=False)
    billing_period: Mapped[str] = mapped_column(
        Enum(*BILLING_PERIODS, name="billing_period"), default="month", nullable=False
    )
    quota_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    quota_window: Mapped[str] = mapped_column(
        Enum(*QUOTA_WINDOWS, name="quota_window"), default="day", nullable=False
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stripe_price_id: Mapped[str | None] = mapped_column(String(120))
    razorpay_plan_id: Mapped[str | None] = mapped_column(String(120))
    plan_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)


class Subscription(PKMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    gateway: Mapped[str] = mapped_column(
        Enum(*GATEWAYS, name="sub_gateway"), default="manual", nullable=False
    )
    gateway_subscription_id: Mapped[str | None] = mapped_column(String(190))
    gateway_customer_id: Mapped[str | None] = mapped_column(String(190))
    status: Mapped[str] = mapped_column(
        Enum(*SUB_STATUS, name="sub_status"), default="active", nullable=False
    )
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime)

    plan: Mapped[Plan] = relationship(lazy="joined")


class PaymentMethod(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "payment_methods"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    gateway: Mapped[str] = mapped_column(Enum(*GATEWAYS, name="pm_gateway"), nullable=False)
    gateway_method_id: Mapped[str] = mapped_column(String(190), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(40))
    last4: Mapped[str | None] = mapped_column(CHAR(4))
    exp_month: Mapped[int | None] = mapped_column(SmallInteger)
    exp_year: Mapped[int | None] = mapped_column(SmallInteger)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Payment(PKMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    gateway: Mapped[str] = mapped_column(Enum(*GATEWAYS, name="pay_gateway"), nullable=False)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(190))
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*PAYMENT_STATUS, name="payment_status"), default="pending", nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    retry_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)


class Invoice(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "invoices"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    payment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("payments.id", ondelete="SET NULL")
    )
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*INVOICE_STATUS, name="invoice_status"), default="open", nullable=False
    )
    line_items: Mapped[list | None] = mapped_column(JSON)
    pdf_url: Mapped[str | None] = mapped_column(String(512))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)


class WebhookEvent(PKMixin, Base):
    __tablename__ = "webhook_events"

    gateway: Mapped[str] = mapped_column(Enum("stripe", "razorpay", name="wh_gateway"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(190), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*WEBHOOK_STATUS, name="webhook_status"), default="received", nullable=False
    )
    error: Mapped[str | None] = mapped_column(String(1024))
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
