"""Merchant schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MerchantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    domain: str | None = None
    logo_url: str | None = None
    description: str | None = None
    trust_score: float
    is_active: bool
    coupon_count: int


class MerchantCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=180)
    domain: str | None = Field(default=None, max_length=190)
    logo_url: str | None = Field(default=None, max_length=512)
    description: str | None = None
    trust_score: float = Field(default=0.5, ge=0, le=1)


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    domain: str | None = Field(default=None, max_length=190)
    logo_url: str | None = Field(default=None, max_length=512)
    description: str | None = None
    trust_score: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None


class AliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=180)
    weight: float = Field(default=1.0, ge=0, le=1)
