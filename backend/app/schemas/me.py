"""Schemas for the authenticated user's dashboard ('me') endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SavedCouponOut(BaseModel):
    id: int
    coupon_uuid: str
    title: str
    code: str | None
    merchant_name: str
    discount_type: str
    discount_value: float | None
    expires_at: datetime | None
    saved_at: datetime


class SaveCouponIn(BaseModel):
    coupon_uuid: str


class WatchlistItemOut(BaseModel):
    id: int
    merchant_id: int
    merchant_name: str
    merchant_slug: str
    created_at: datetime


class WatchlistIn(BaseModel):
    merchant_id: int


class DealAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    merchant_id: int | None
    keyword: str | None
    min_discount: float | None
    channel: str
    is_active: bool
    created_at: datetime


class DealAlertIn(BaseModel):
    merchant_id: int | None = None
    keyword: str | None = Field(default=None, max_length=190)
    min_discount: float | None = None
    channel: str = "in_app"


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    body: str | None
    read_at: datetime | None
    created_at: datetime


class SearchHistoryOut(BaseModel):
    id: int
    raw_query: str
    normalized_query: str | None
    results_count: int
    created_at: datetime


class ReferralSummary(BaseModel):
    referral_code: str | None
    total: int
    converted: int
    rewarded: int
    invite_url: str


class SubscriptionOut(BaseModel):
    plan: str
    plan_name: str
    status: str
    quota_limit: int
    quota_window: str
    current_period_end: datetime | None
    cancel_at_period_end: bool
