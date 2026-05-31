"""Authentication service: registration, login, token issuance & rotation.

Token model
-----------
* Access token: short-lived JWT carrying ``sub``, ``role`` and ``perms``.
* Refresh token: opaque random string. Only its SHA-256 hash is stored. Tokens
  belong to a ``family_id``; on refresh the presented token is revoked and a new
  one issued in the same family. If a *revoked* token from a family is presented
  again, we treat it as theft and revoke the whole family.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.models.user import RefreshToken, User
from app.schemas.auth import TokenPair
from app.services import user_service


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    referral_code: str | None = None,
) -> User:
    email = email.lower().strip()
    if await user_service.get_by_email(db, email):
        raise ConflictError("An account with this email already exists.")

    role = await user_service.get_default_role(db, "user")
    if role is None:
        raise AuthenticationError("Default role is not configured. Run the seed migration.")

    referred_by = None
    if referral_code:
        referrer = await user_service.get_by_referral_code(db, referral_code.upper())
        if referrer:
            referred_by = referrer.id

    user = User(
        uuid=security.new_uuid(),
        email=email,
        password_hash=security.hash_password(password),
        full_name=full_name,
        role_id=role.id,
        status="active",
        referral_code=security.generate_referral_code(),
        referred_by=referred_by,
    )
    db.add(user)
    await db.flush()
    # Reload with role + permissions eagerly populated.
    return await user_service.get_by_id(db, user.id)  # type: ignore[return-value]


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = await user_service.get_by_email(db, email.lower().strip())
    # Constant-ish work whether or not the user exists to limit user enumeration.
    if user is None:
        security.verify_password(password, security.hash_password("dummy-password"))
        raise AuthenticationError("Invalid email or password.")
    if not security.verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationError("This account is not active.")
    return user


def _access_token_for(user: User) -> str:
    perms = sorted(user.role.permission_slugs()) if user.role else []
    return security.create_access_token(
        user.id,
        role=user.role.slug if user.role else "user",
        permissions=perms,
    )


async def issue_token_pair(
    db: AsyncSession,
    user: User,
    *,
    family_id: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    """Create a new access+refresh pair and persist the refresh token hash."""
    raw_refresh = security.generate_refresh_token()
    record = RefreshToken(
        user_id=user.id,
        token_hash=security.hash_token(raw_refresh),
        family_id=family_id or security.new_family_id(),
        user_agent=(user_agent or "")[:255] or None,
        ip_address=ip_address,
        expires_at=security.refresh_expiry(),
    )
    db.add(record)
    await db.flush()

    return TokenPair(
        access_token=_access_token_for(user),
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def rotate_refresh_token(
    db: AsyncSession,
    raw_refresh: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, TokenPair]:
    token_hash = security.hash_token(raw_refresh)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    token = (await db.execute(stmt)).scalar_one_or_none()

    if token is None:
        raise AuthenticationError("Invalid refresh token.")

    # Reuse detection: a previously revoked token implies theft -> kill the family.
    if token.revoked_at is not None:
        await _revoke_family(db, token.family_id)
        raise AuthenticationError("Refresh token reuse detected; session revoked.")

    if token.expires_at <= datetime.utcnow():
        raise AuthenticationError("Refresh token has expired.")

    user = await user_service.get_by_id(db, token.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Account is no longer active.")

    # Revoke the presented token, then mint a new one in the same family.
    token.revoked_at = datetime.utcnow()
    await db.flush()
    pair = await issue_token_pair(
        db, user, family_id=token.family_id, user_agent=user_agent, ip_address=ip_address
    )
    return user, pair


async def revoke_refresh_token(db: AsyncSession, raw_refresh: str) -> None:
    token_hash = security.hash_token(raw_refresh)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.utcnow())
    )


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.utcnow())
    )


async def _revoke_family(db: AsyncSession, family_id: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.utcnow())
    )
