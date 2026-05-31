"""User lookups and mutations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.rbac import Role
from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = (
        select(User)
        .where(User.email == email.lower())
        .options(joinedload(User.role).selectinload(Role.permissions))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(joinedload(User.role).selectinload(Role.permissions))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_uuid(db: AsyncSession, uuid: str) -> User | None:
    stmt = (
        select(User)
        .where(User.uuid == uuid)
        .options(joinedload(User.role).selectinload(Role.permissions))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_referral_code(db: AsyncSession, code: str) -> User | None:
    stmt = select(User).where(User.referral_code == code)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_default_role(db: AsyncSession, slug: str = "user") -> Role | None:
    stmt = select(Role).where(Role.slug == slug).options(selectinload(Role.permissions))
    return (await db.execute(stmt)).scalar_one_or_none()
