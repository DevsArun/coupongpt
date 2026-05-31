"""User engagement models: saved coupons, watchlists, alerts, notifications, referrals."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, PKMixin

ALERT_CHANNELS = ("email", "push", "in_app")
REFERRAL_STATUS = ("pending", "converted", "rewarded")


class SavedCoupon(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "saved_coupons"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    coupon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False
    )


class Watchlist(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "watchlists"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    merchant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )


class DealAlert(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "deal_alerts"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    merchant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="CASCADE")
    )
    keyword: Mapped[str | None] = mapped_column(String(190))
    min_discount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    channel: Mapped[str] = mapped_column(
        Enum(*ALERT_CHANNELS, name="alert_channel"), default="in_app", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime)


class Notification(PKMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(190), nullable=False)
    body: Mapped[str | None] = mapped_column(String(1024))
    data: Mapped[dict | None] = mapped_column(JSON)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Referral(PKMixin, Base):
    __tablename__ = "referrals"

    referrer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    referred_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*REFERRAL_STATUS, name="referral_status"), default="pending", nullable=False
    )
    reward_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    converted_at: Mapped[datetime | None] = mapped_column(DateTime)
