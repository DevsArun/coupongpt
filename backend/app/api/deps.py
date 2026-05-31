"""FastAPI dependencies: DB session, current user, and RBAC guards.

Usage::

    @router.get("/admin/coupons")
    async def list_coupons(user: User = Depends(require_permission("coupons.read"))):
        ...
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models.user import User
from app.services import user_service

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    request: Request,
) -> str | None:
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    # Fallback: allow an access token in an HttpOnly cookie (set by PHP tier).
    return request.cookies.get("access_token")


async def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    token = _extract_token(credentials, request)
    if not token:
        raise AuthenticationError("Authentication required.")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid access token.") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise AuthenticationError("Invalid token type.")

    sub = payload.get("sub")
    if sub is None:
        raise AuthenticationError("Malformed token.")

    user = await user_service.get_by_id(db, int(sub))
    if user is None or not user.is_active:
        raise AuthenticationError("Account not found or inactive.")
    return user


async def get_optional_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User | None:
    """Like ``get_current_user`` but returns None instead of raising.

    Used by endpoints (e.g. search) that work for anonymous users but unlock
    extra behaviour when authenticated.
    """
    token = _extract_token(credentials, request)
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            return None
        sub = payload.get("sub")
        if sub is None:
            return None
        user = await user_service.get_by_id(db, int(sub))
        return user if user and user.is_active else None
    except jwt.PyJWTError:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_permission(*permission_slugs: str):
    """Dependency factory enforcing that the user holds *all* given permissions.

    ``super_admin`` implicitly passes every check.
    """

    async def _guard(user: CurrentUser) -> User:
        role_slug = user.role.slug if user.role else "user"
        if role_slug == "super_admin":
            return user
        held = user.role.permission_slugs() if user.role else set()
        missing = [p for p in permission_slugs if p not in held]
        if missing:
            raise PermissionDeniedError(
                "You do not have permission to perform this action.",
                detail={"missing_permissions": missing},
            )
        return user

    return _guard


def require_role(*role_slugs: str):
    """Dependency factory enforcing the user holds one of the given roles."""

    allowed = set(role_slugs)

    async def _guard(user: CurrentUser) -> User:
        role_slug = user.role.slug if user.role else "user"
        if role_slug == "super_admin" or role_slug in allowed:
            return user
        raise PermissionDeniedError("Insufficient role for this action.")

    return _guard
