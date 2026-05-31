"""Admin panel schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DashboardStats(BaseModel):
    users_total: int
    coupons_total: int
    coupons_active: int
    coupons_pending: int
    merchants_total: int
    sources_total: int
    searches_today: int
    active_subscriptions: int
    revenue_month_cents: int
    avg_search_latency_ms: float


class DashboardResponse(BaseModel):
    stats: DashboardStats
    top_merchants: list[dict]
    search_trend: list[dict]


class SourceCreate(BaseModel):
    url: str = Field(min_length=4, max_length=1024)
    type: str = Field(description="merchant_page|promo_page|rss|sitemap|newsletter|user_submission")
    merchant_id: int | None = None
    trust_score: float = Field(default=0.5, ge=0, le=1)
    crawl_frequency: int = Field(default=86400, ge=300)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    merchant_id: int | None
    type: str
    url: str
    trust_score: float
    crawl_frequency: int
    is_active: bool
    last_crawled_at: datetime | None
    last_status: str | None


class CrawlJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int
    status: str
    stage: str | None
    items_found: int
    items_ingested: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class AIProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    is_enabled: bool
    priority: int
    model: str | None
    timeout_s: int


class AIProviderUpdate(BaseModel):
    is_enabled: bool | None = None
    priority: int | None = None
    model: str | None = None
    timeout_s: int | None = Field(default=None, ge=1, le=60)


class FeatureFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    flag_key: str
    description: str | None
    is_enabled: bool
    rollout_pct: int


class FeatureFlagUpdate(BaseModel):
    is_enabled: bool | None = None
    rollout_pct: int | None = Field(default=None, ge=0, le=100)


class SettingUpdate(BaseModel):
    value: dict | list | str | int | float | bool


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int | None
    action: str
    entity_type: str | None
    entity_id: str | None
    ip_address: str | None
    created_at: datetime


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    uuid: str
    email: str
    full_name: str | None
    status: str
    role_id: int
    created_at: datetime
    last_login_at: datetime | None


class AdminUserUpdate(BaseModel):
    status: str | None = Field(default=None, description="active|suspended|pending|deleted")
    role_slug: str | None = None
