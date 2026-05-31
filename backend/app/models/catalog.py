"""Merchant, merchant alias, and category models."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, PKMixin, TimestampMixin


class Merchant(PKMixin, TimestampMixin, Base):
    __tablename__ = "merchants"

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(190))
    logo_url: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    trust_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    coupon_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    aliases: Mapped[list["MerchantAlias"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan", lazy="selectin"
    )


class MerchantAlias(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "merchant_aliases"

    merchant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(180), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 3), default=1.0, nullable=False)

    merchant: Mapped[Merchant] = relationship(back_populates="aliases")


class Category(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="SET NULL")
    )
