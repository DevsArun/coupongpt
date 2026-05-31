"""Authentication endpoints: register, login, refresh, logout, profile."""
from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password, verify_password
from app.core.exceptions import ValidationAppError
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.schemas.user import PasswordChange, UserPublic, UserUpdate
from app.services import auth_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, db: DbSession) -> AuthResponse:
    ip, ua = _client_meta(request)
    user = await auth_service.register_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        referral_code=payload.referral_code,
    )
    tokens = await auth_service.issue_token_pair(db, user, user_agent=ua, ip_address=ip)
    await record_audit(db, action="auth.register", actor_id=user.id, ip_address=ip, user_agent=ua)
    return AuthResponse(user=UserPublic.from_orm_user(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, db: DbSession) -> AuthResponse:
    ip, ua = _client_meta(request)
    user = await auth_service.authenticate(db, email=payload.email, password=payload.password)
    tokens = await auth_service.issue_token_pair(db, user, user_agent=ua, ip_address=ip)
    from datetime import datetime

    user.last_login_at = datetime.utcnow()
    await record_audit(db, action="auth.login", actor_id=user.id, ip_address=ip, user_agent=ua)
    return AuthResponse(user=UserPublic.from_orm_user(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, request: Request, db: DbSession) -> TokenPair:
    ip, ua = _client_meta(request)
    _user, tokens = await auth_service.rotate_refresh_token(
        db, payload.refresh_token, user_agent=ua, ip_address=ip
    )
    return tokens


@router.post("/logout", response_model=Message)
async def logout(payload: RefreshRequest, db: DbSession) -> Message:
    await auth_service.revoke_refresh_token(db, payload.refresh_token)
    return Message(message="Logged out.")


@router.post("/logout-all", response_model=Message)
async def logout_all(user: CurrentUser, db: DbSession) -> Message:
    await auth_service.revoke_all_for_user(db, user.id)
    return Message(message="All sessions revoked.")


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic.from_orm_user(user)


@router.patch("/me", response_model=UserPublic)
async def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession) -> UserPublic:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.timezone is not None:
        user.timezone = payload.timezone
    await db.flush()
    return UserPublic.from_orm_user(user)


@router.post("/change-password", response_model=Message)
async def change_password(
    payload: PasswordChange, user: CurrentUser, request: Request, db: DbSession
) -> Message:
    if not verify_password(payload.current_password, user.password_hash):
        raise ValidationAppError("Current password is incorrect.")
    user.password_hash = hash_password(payload.new_password)
    await db.flush()
    # Force re-login everywhere after a password change.
    await auth_service.revoke_all_for_user(db, user.id)
    ip, ua = _client_meta(request)
    await record_audit(
        db, action="auth.password_change", actor_id=user.id, ip_address=ip, user_agent=ua
    )
    return Message(message="Password changed. Please log in again.")
