"""Search analytics and synonym models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import PKMixin, TimestampMixin


class SearchQuery(PKMixin, Base):
    __tablename__ = "search_queries"

    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    raw_query: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_query: Mapped[str | None] = mapped_column(String(512))
    detected_merchant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="SET NULL")
    )
    intent: Mapped[dict | None] = mapped_column(JSON)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_provider: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Synonym(PKMixin, TimestampMixin, Base):
    __tablename__ = "synonyms"

    term: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    synonyms: Mapped[list] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
