"""Coupon and related models: categories link, validation events, feedback."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TimestampMixin

DISCOUNT_TYPES = ("percentage", "fixed", "bogo", "free_shipping", "trial", "other")
COUPON_STATUS = ("draft", "active", "expired", "revoked", "pending_review")
VALIDATION_EVENT_TYPES = ("scored", "revalidated", "expired", "flagged", "restored")


class CouponCategory(Base):
    __tablename__ = "coupon_categories"

    coupon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coupons.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )


class Coupon(PKMixin, TimestampMixin, Base):
    __tablename__ = "coupons"

    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    merchant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sources.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(String(120))
    discount_type: Mapped[str] = mapped_column(
        Enum(*DISCOUNT_TYPES, name="discount_type"), default="other", nullable=False
    )
    discount_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    landing_url: Mapped[str | None] = mapped_column(String(1024))
    terms: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*COUPON_STATUS, name="coupon_status"), default="pending_review", nullable=False
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    # ---- six component scores ----
    source_trust_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    duplicate_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0, nullable=False)
    success_rate_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    expiry_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    ranking_score: Mapped[float] = mapped_column(Numeric(6, 4), default=0.5, nullable=False)

    # ---- engagement counters ----
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fail_reports: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime)

    merchant: Mapped["Merchant"] = relationship(lazy="joined")  # noqa: F821


class CouponValidationEvent(PKMixin, Base):
    __tablename__ = "coupon_validation_events"

    coupon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        Enum(*VALIDATION_EVENT_TYPES, name="validation_event_type"), nullable=False
    )
    old_score: Mapped[float | None] = mapped_column(Numeric(6, 4))
    new_score: Mapped[float | None] = mapped_column(Numeric(6, 4))
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class CouponFeedback(PKMixin, Base):
    __tablename__ = "coupon_feedback"

    coupon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    worked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
