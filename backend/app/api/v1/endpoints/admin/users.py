"""Admin user, subscription, and billing management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DbSession, require_permission
from app.core.exceptions import NotFoundError
from app.models.billing import Invoice, Payment, Subscription
from app.models.rbac import Role
from app.models.user import User
from app.schemas.admin import AdminUserOut, AdminUserUpdate
from app.schemas.common import Message, Page
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/users", response_model=Page[AdminUserOut])
async def list_users(
    db: DbSession,
    q: str | None = Query(None, max_length=120),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("users.read")),
) -> Page[AdminUserOut]:
    base = select(User)
    if q:
        base = base.where(User.email.ilike(f"%{q}%"))
    if status:
        base = base.where(User.status == status)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(base.order_by(User.created_at.desc()).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()
    return Page.create([AdminUserOut.model_validate(r) for r in rows], total, page, page_size)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: DbSession,
    actor: CurrentUser,
    _: object = Depends(require_permission("users.write")),
) -> AdminUserOut:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found.")
    if payload.status is not None:
        user.status = payload.status
    if payload.role_slug is not None:
        role = (await db.execute(select(Role).where(Role.slug == payload.role_slug))).scalar_one_or_none()
        if role is None:
            raise NotFoundError("Role not found.")
        user.role_id = role.id
    await db.flush()
    await record_audit(db, action="user.update", actor_id=actor.id, entity_type="user", entity_id=user_id)
    return AdminUserOut.model_validate(user)


@router.get("/subscriptions")
async def list_subscriptions(
    db: DbSession,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("subscriptions.read")),
) -> dict:
    base = select(Subscription).options(joinedload(Subscription.plan))
    if status:
        base = base.where(Subscription.status == status)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(
            base.order_by(Subscription.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
    ).scalars().all()
    items = [
        {
            "id": s.id,
            "user_id": s.user_id,
            "plan": s.plan.slug if s.plan else None,
            "status": s.status,
            "gateway": s.gateway,
            "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            "cancel_at_period_end": s.cancel_at_period_end,
        }
        for s in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/billing/payments")
async def list_payments(
    db: DbSession,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("subscriptions.read")),
) -> dict:
    base = select(Payment)
    if status:
        base = base.where(Payment.status == status)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(base.order_by(Payment.created_at.desc()).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()
    items = [
        {
            "id": p.id,
            "user_id": p.user_id,
            "amount_cents": p.amount_cents,
            "currency": p.currency,
            "status": p.status,
            "gateway": p.gateway,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        }
        for p in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/billing/invoices")
async def list_invoices(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: object = Depends(require_permission("subscriptions.read")),
) -> dict:
    base = select(Invoice)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    rows = (
        await db.execute(base.order_by(Invoice.created_at.desc()).limit(page_size).offset((page - 1) * page_size))
    ).scalars().all()
    items = [
        {
            "id": i.id,
            "number": i.number,
            "user_id": i.user_id,
            "amount_cents": i.amount_cents,
            "currency": i.currency,
            "status": i.status,
            "issued_at": i.issued_at.isoformat() if i.issued_at else None,
        }
        for i in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
