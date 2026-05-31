"""Ingestion source and crawl job models."""
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, PKMixin, TimestampMixin

SOURCE_TYPES = (
    "merchant_page",
    "promo_page",
    "rss",
    "sitemap",
    "newsletter",
    "user_submission",
)
CRAWL_STATUS = ("queued", "running", "succeeded", "failed", "skipped")


class Source(PKMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    merchant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("merchants.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(Enum(*SOURCE_TYPES, name="source_type"), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    trust_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5, nullable=False)
    crawl_frequency: Mapped[int] = mapped_column(Integer, default=86400, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_status: Mapped[str | None] = mapped_column(String(32))

    crawl_jobs: Mapped[list["CrawlJob"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class CrawlJob(PKMixin, CreatedAtMixin, Base):
    __tablename__ = "crawl_jobs"

    source_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(*CRAWL_STATUS, name="crawl_status"), default="queued", nullable=False
    )
    stage: Mapped[str | None] = mapped_column(String(32))
    items_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    source: Mapped[Source] = relationship(back_populates="crawl_jobs")
