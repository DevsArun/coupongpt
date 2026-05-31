"""Billing endpoints: plans, checkout, subscription management, invoices, webhooks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, require_permission
from app.models.billing import Invoice, Payment
from app.schemas.billing import (
    CancelIn,
    ChangePlanIn,
    CheckoutIn,
    InvoiceOut,
    PaymentOut,
    PlanOut,
)
from app.schemas.common import Message
from app.services import billing_service
from app.services.audit_service import record_audit

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut], summary="Public: list subscription plans")
async def plans(db: DbSession) -> list[PlanOut]:
    return [PlanOut.model_validate(p) for p in await billing_service.list_public_plans(db)]


@router.post("/checkout")
async def checkout(payload: CheckoutIn, user: CurrentUser, db: DbSession) -> dict:
    result = await billing_service.create_checkout(db, user, payload.plan_slug, payload.gateway)
    await record_audit(db, action="billing.checkout", actor_id=user.id, metadata={"plan": payload.plan_slug})
    return result


@router.post("/change-plan")
async def change_plan(payload: ChangePlanIn, user: CurrentUser, db: DbSession) -> dict:
    return await billing_service.change_plan(db, user, payload.plan_slug, payload.gateway)


@router.post("/cancel", response_model=Message)
async def cancel(payload: CancelIn, user: CurrentUser, db: DbSession) -> Message:
    sub = await billing_service.cancel_subscription(db, user, at_period_end=payload.at_period_end)
    await record_audit(db, action="billing.cancel", actor_id=user.id, entity_type="subscription", entity_id=sub.id)
    return Message(
        message="Subscription will end at the period close."
        if payload.at_period_end
        else "Subscription canceled."
    )


@router.get("/invoices", response_model=list[InvoiceOut])
async def my_invoices(user: CurrentUser, db: DbSession) -> list[InvoiceOut]:
    rows = (
        await db.execute(
            select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc())
        )
    ).scalars().all()
    return [InvoiceOut.model_validate(r) for r in rows]


@router.get("/payments", response_model=list[PaymentOut])
async def my_payments(user: CurrentUser, db: DbSession) -> list[PaymentOut]:
    rows = (
        await db.execute(
            select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
        )
    ).scalars().all()
    return [PaymentOut.model_validate(r) for r in rows]


@router.post("/refund/{payment_id}", response_model=Message)
async def refund(
    payment_id: int,
    db: DbSession,
    user: CurrentUser,
    _: object = Depends(require_permission("billing.refund")),
) -> Message:
    payment = await billing_service.refund_payment(db, payment_id)
    await record_audit(db, action="billing.refund", actor_id=user.id, entity_type="payment", entity_id=payment_id)
    return Message(message=f"Payment refunded (status: {payment.status}).")


# ---- Webhooks (public, raw body, signature-verified) ----
@router.post("/webhooks/stripe", include_in_schema=True)
async def stripe_webhook(request: Request, db: DbSession) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    return await billing_service.process_webhook(db, "stripe", payload, signature)


@router.post("/webhooks/razorpay", include_in_schema=True)
async def razorpay_webhook(request: Request, db: DbSession) -> dict:
    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    return await billing_service.process_webhook(db, "razorpay", payload, signature)
