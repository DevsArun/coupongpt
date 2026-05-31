"""Coupon-facing schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    title: str
    description: str | None = None
    code: str | None = None
    merchant_id: int
    discount_type: str
    discount_value: float | None = None
    currency: str | None = None
    landing_url: str | None = None
    terms: str | None = None
    status: str
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    ranking_score: float
    views: int
    clicks: int
    success_reports: int
    fail_reports: int
    created_at: datetime


class CouponScores(BaseModel):
    source_trust_score: float
    freshness_score: float
    confidence_score: float
    duplicate_score: float
    success_rate_score: float
    expiry_score: float
    ranking_score: float


class CouponSubmission(BaseModel):
    merchant_slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=3, max_length=255)
    code: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    landing_url: str | None = Field(default=None, max_length=1024)


class FeedbackIn(BaseModel):
    worked: bool
    comment: str | None = Field(default=None, max_length=512)


class CouponCreate(BaseModel):
    merchant_id: int
    title: str = Field(min_length=3, max_length=255)
    code: str | None = Field(default=None, max_length=120)
    description: str | None = None
    discount_type: str = "other"
    discount_value: float | None = None
    currency: str | None = Field(default=None, max_length=3)
    landing_url: str | None = Field(default=None, max_length=1024)
    terms: str | None = None
    expires_at: datetime | None = None


class CouponUpdate(BaseModel):
    title: str | None = None
    code: str | None = None
    description: str | None = None
    discount_type: str | None = None
    discount_value: float | None = None
    currency: str | None = None
    landing_url: str | None = None
    terms: str | None = None
    status: str | None = None
    expires_at: datetime | None = None
