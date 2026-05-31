"""User-facing schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    email: EmailStr
    full_name: str | None = None
    role: str = "user"
    status: str
    referral_code: str | None = None
    timezone: str = "UTC"
    created_at: datetime

    @classmethod
    def from_orm_user(cls, user) -> "UserPublic":
        return cls(
            id=user.id,
            uuid=user.uuid,
            email=user.email,
            full_name=user.full_name,
            role=user.role.slug if user.role else "user",
            status=user.status,
            referral_code=user.referral_code,
            timezone=user.timezone,
            created_at=user.created_at,
        )


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=150)
    timezone: str | None = Field(default=None, max_length=64)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
