"""System models: AI providers, AI usage logs, feature flags, settings, queue jobs."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, PKMixin, TimestampMixin

QUEUE_STATUS = ("queued", "running", "succeeded", "failed")


class AIProvider(PKMixin, TimestampMixin, Base):
    __tablename__ = "ai_providers"

    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    timeout_s: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON)


class AIUsageLog(PKMixin, Base):
    __tablename__ = "ai_usage_logs"

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class FeatureFlag(PKMixin, Base):
    __tablename__ = "feature_flags"

    flag_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollout_pct: Mapped[int] = mapped_column(SmallInteger, default=100, nullable=False)
    flag_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Setting(PKMixin, Base):
    __tablename__ = "settings"

    setting_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class QueueJob(PKMixin, TimestampMixin, Base):
    __tablename__ = "queue_jobs"

    queue: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    job_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        Enum(*QUEUE_STATUS, name="queue_status"), default="queued", nullable=False
    )
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    error: Mapped[str | None] = mapped_column(Text)
