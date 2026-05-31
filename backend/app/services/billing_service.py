"""Billing service: plans, checkout, subscriptions, invoices, webhooks, refunds.

Supports Stripe and Razorpay through the gateway abstraction, plus a manual/demo
path when no gateway keys are configured. All webhook processing is idempotent
(keyed on the provider event id in ``webhook_events``).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.base import CheckoutResult, GatewayError, PaymentGateway
from app.billing.razorpay_gateway import RazorpayGateway
from app.billing.stripe_gateway import StripeGateway
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.billing import Invoice, Payment, Plan, Subscription, WebhookEvent
from app.models.user import User

logger = get_logger("billing.service")


def get_gateway(slug: str) -> PaymentGateway:
    if slug == "stripe":
        return StripeGateway(
            api_key=settings.stripe_secret_key,
            webhook_secret=settings.stripe_webhook_secret,
        )
    if slug == "razorpay":
        return RazorpayGateway(
            api_key=settings.razorpay_key_id,
            secret=settings.razorpay_key_secret,
            webhook_secret=settings.razorpay_webhook_secret,
        )
    raise NotFoundError(f"Unknown gateway: {slug}")


async def list_public_plans(db: AsyncSession) -> list[Plan]:
    stmt = (
        select(Plan)
        .where(Plan.is_active.is_(True), Plan.is_public.is_(True))
        .order_by(Plan.sort_order.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_plan(db: AsyncSession, slug: str) -> Plan:
    plan = (await db.execute(select(Plan).where(Plan.slug == slug))).scalar_one_or_none()
    if plan is None:
        raise NotFoundError("Plan not found.")
    return plan


def _period_end(plan: Plan, start: datetime) -> datetime:
    if plan.billing_period == "year":
        return start + timedelta(days=365)
    if plan.billing_period == "day":
        return start + timedelta(days=1)
    if plan.billing_period == "lifetime":
        return start + timedelta(days=365 * 100)
    return start + timedelta(days=30)  # month / custom default


async def _generate_invoice_number(db: AsyncSession) -> str:
    year = datetime.utcnow().year
    count = int(
        (await db.execute(select(func.count()).select_from(Invoice))).scalar_one()
    )
    return f"INV-{year}-{count + 1:06d}"


async def activate_subscription(
    db: AsyncSession,
    user: User,
    plan: Plan,
    *,
    gateway: str,
    gateway_subscription_id: str | None = None,
    gateway_customer_id: str | None = None,
    status: str = "active",
) -> Subscription:
    # Cancel any other currently-active subscriptions (single active plan model).
    await db.execute(
        update(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status.in_(("active", "trialing", "past_due")),
        )
        .values(status="canceled", canceled_at=datetime.utcnow())
    )

    now = datetime.utcnow()
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        gateway=gateway,
        gateway_subscription_id=gateway_subscription_id,
        gateway_customer_id=gateway_customer_id,
        status=status,
        current_period_start=now,
        current_period_end=_period_end(plan, now),
    )
    db.add(sub)
    await db.flush()
    return sub


async def record_payment(
    db: AsyncSession,
    user: User,
    subscription: Subscription | None,
    *,
    amount_cents: int,
    currency: str,
    gateway: str,
    gateway_payment_id: str | None,
    status: str = "succeeded",
) -> Payment:
    payment = Payment(
        user_id=user.id,
        subscription_id=subscription.id if subscription else None,
        gateway=gateway,
        gateway_payment_id=gateway_payment_id,
        amount_cents=amount_cents,
        currency=currency,
        status=status,
        paid_at=datetime.utcnow() if status == "succeeded" else None,
    )
    db.add(payment)
    await db.flush()

    if status == "succeeded" and amount_cents > 0:
        invoice = Invoice(
            user_id=user.id,
            subscription_id=subscription.id if subscription else None,
            payment_id=payment.id,
            number=await _generate_invoice_number(db),
            amount_cents=amount_cents,
            currency=currency,
            status="paid",
            line_items=[{"description": "Subscription", "amount_cents": amount_cents}],
            issued_at=datetime.utcnow(),
            paid_at=datetime.utcnow(),
        )
        db.add(invoice)
        await db.flush()
    return payment


async def create_checkout(
    db: AsyncSession, user: User, plan_slug: str, gateway_slug: str
) -> dict:
    plan = await get_plan(db, plan_slug)

    # Free plan: just (re)activate, no payment.
    if plan.price_cents == 0:
        await activate_subscription(db, user, plan, gateway="manual")
        return {"mode": "activated", "plan": plan.slug, "message": "Free plan activated."}

    gateway = get_gateway(gateway_slug)
    base = settings.cors_origin_list[0] if settings.cors_origin_list else ""
    try:
        result: CheckoutResult = await gateway.create_checkout(
            plan=plan,
            user=user,
            success_url=f"{base}/app/billing?status=success",
            cancel_url=f"{base}/app/billing?status=cancel",
        )
    except GatewayError as exc:
        logger.warning("checkout_gateway_error", error=str(exc))
        result = CheckoutResult(gateway=gateway_slug, mode="demo")

    if result.mode == "demo":
        # No real gateway configured -> activate + record a paid payment (demo).
        sub = await activate_subscription(
            db, user, plan, gateway=gateway_slug,
            gateway_subscription_id=result.gateway_subscription_id,
            gateway_customer_id=result.gateway_customer_id,
        )
        await record_payment(
            db, user, sub,
            amount_cents=plan.price_cents, currency=plan.currency,
            gateway=gateway_slug, gateway_payment_id=f"demo_{sub.id}", status="succeeded",
        )
        return {"mode": "activated", "plan": plan.slug, "message": "Subscription activated (demo mode)."}

    return {
        "mode": "redirect",
        "checkout_url": result.checkout_url,
        "client_payload": result.client_payload,
        "plan": plan.slug,
    }


async def cancel_subscription(db: AsyncSession, user: User, *, at_period_end: bool = True) -> Subscription:
    sub = (
        await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id, Subscription.status.in_(("active", "trialing")))
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if sub is None:
        raise NotFoundError("No active subscription to cancel.")
    if at_period_end:
        sub.cancel_at_period_end = True
    else:
        sub.status = "canceled"
        sub.canceled_at = datetime.utcnow()
    await db.flush()
    return sub


async def change_plan(db: AsyncSession, user: User, new_plan_slug: str, gateway_slug: str = "manual") -> dict:
    return await create_checkout(db, user, new_plan_slug, gateway_slug)


async def refund_payment(db: AsyncSession, payment_id: int) -> Payment:
    payment = (await db.execute(select(Payment).where(Payment.id == payment_id))).scalar_one_or_none()
    if payment is None:
        raise NotFoundError("Payment not found.")
    if payment.status != "succeeded":
        raise ConflictError("Only succeeded payments can be refunded.")
    ok = True
    if payment.gateway in ("stripe", "razorpay") and payment.gateway_payment_id and not payment.gateway_payment_id.startswith("demo_"):
        gateway = get_gateway(payment.gateway)
        ok = await gateway.refund(payment.gateway_payment_id, amount_cents=payment.amount_cents)
    payment.status = "refunded" if ok else payment.status
    await db.flush()
    return payment


async def retry_failed_payments(db: AsyncSession) -> int:
    """Find failed payments whose retry time is due and bump their retry counter.

    In a real deployment this would re-attempt the gateway charge; here we mark
    them for re-attempt and cap retries.
    """
    now = datetime.utcnow()
    rows = (
        await db.execute(
            select(Payment).where(
                Payment.status == "failed",
                Payment.retry_count < 3,
                Payment.next_retry_at.is_not(None),
                Payment.next_retry_at <= now,
            )
        )
    ).scalars().all()
    for p in rows:
        p.retry_count += 1
        p.next_retry_at = now + timedelta(hours=24 * p.retry_count)
    await db.flush()
    return len(rows)


# ------------------------------------------------------------- webhooks
async def process_webhook(db: AsyncSession, gateway_slug: str, payload: bytes, signature: str | None) -> dict:
    gateway = get_gateway(gateway_slug)
    event = gateway.verify_and_parse_webhook(payload, signature)

    if not event.event_id:
        return {"status": "ignored", "reason": "no event id"}

    # Idempotency guard.
    exists = (
        await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.gateway == gateway_slug, WebhookEvent.event_id == event.event_id
            )
        )
    ).scalar_one_or_none()
    if exists:
        return {"status": "duplicate"}

    record = WebhookEvent(
        gateway=gateway_slug,
        event_id=event.event_id,
        event_type=event.event_type,
        payload=event.raw or {},
        status="received",
        received_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()

    try:
        await _apply_event(db, gateway_slug, event)
        record.status = "processed"
        record.processed_at = datetime.utcnow()
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)[:1000]
        logger.error("webhook_apply_failed", gateway=gateway_slug, error=str(exc))
    await db.flush()
    return {"status": record.status}


async def _find_user(db: AsyncSession, event) -> User | None:
    raw = event.raw or {}
    # Stripe: metadata.user_id on the object; Razorpay: notes.user_id
    obj = raw.get("data", {}).get("object", {}) if "data" in raw else {}
    user_id = (obj.get("metadata") or {}).get("user_id")
    if not user_id:
        notes = (
            raw.get("payload", {}).get("subscription", {}).get("entity", {}).get("notes")
            if "payload" in raw else None
        )
        user_id = (notes or {}).get("user_id")
    if user_id:
        return (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    if event.gateway_customer_id:
        sub = (
            await db.execute(
                select(Subscription).where(Subscription.gateway_customer_id == event.gateway_customer_id)
            )
        ).scalar_one_or_none()
        if sub:
            return (await db.execute(select(User).where(User.id == sub.user_id))).scalar_one_or_none()
    return None


async def _apply_event(db: AsyncSession, gateway_slug: str, event) -> None:
    if event.status == "succeeded":
        user = await _find_user(db, event)
        if user is None:
            return
        # Determine plan from metadata when present, else keep current.
        raw = event.raw or {}
        obj = raw.get("data", {}).get("object", {}) if "data" in raw else {}
        plan_slug = (obj.get("metadata") or {}).get("plan_slug")
        sub = None
        if plan_slug:
            plan = (await db.execute(select(Plan).where(Plan.slug == plan_slug))).scalar_one_or_none()
            if plan:
                sub = await activate_subscription(
                    db, user, plan, gateway=gateway_slug,
                    gateway_subscription_id=event.gateway_subscription_id,
                    gateway_customer_id=event.gateway_customer_id,
                )
        if event.amount_cents:
            await record_payment(
                db, user, sub,
                amount_cents=int(event.amount_cents), currency=event.currency or "USD",
                gateway=gateway_slug, gateway_payment_id=event.gateway_payment_id, status="succeeded",
            )
    elif event.status == "failed":
        if event.gateway_subscription_id:
            await db.execute(
                update(Subscription)
                .where(Subscription.gateway_subscription_id == event.gateway_subscription_id)
                .values(status="past_due")
            )
    elif event.status == "canceled":
        if event.gateway_subscription_id:
            await db.execute(
                update(Subscription)
                .where(Subscription.gateway_subscription_id == event.gateway_subscription_id)
                .values(status="canceled", canceled_at=datetime.utcnow())
            )
