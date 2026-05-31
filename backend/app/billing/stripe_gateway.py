"""Stripe gateway implementation (lazy SDK import so the app boots without it)."""
from __future__ import annotations

import json

from app.billing.base import CheckoutResult, GatewayError, PaymentGateway, WebhookEvent
from app.core.logging import get_logger

logger = get_logger("billing.stripe")


class StripeGateway(PaymentGateway):
    slug = "stripe"

    def _client(self):
        try:
            import stripe
        except ImportError as exc:  # pragma: no cover
            raise GatewayError("stripe SDK is not installed") from exc
        stripe.api_key = self.api_key
        return stripe

    async def create_checkout(self, *, plan, user, success_url: str, cancel_url: str) -> CheckoutResult:
        if not self.is_configured or not plan.stripe_price_id:
            # Demo mode: no key or no configured price -> activate directly.
            return CheckoutResult(gateway=self.slug, mode="demo")

        stripe = self._client()
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user.email,
                client_reference_id=str(user.id),
                metadata={"user_id": str(user.id), "plan_slug": plan.slug},
            )
        except Exception as exc:  # noqa: BLE001
            raise GatewayError(f"Stripe checkout failed: {exc}") from exc

        return CheckoutResult(
            gateway=self.slug,
            mode="redirect",
            checkout_url=session.get("url"),
            gateway_customer_id=session.get("customer"),
        )

    def verify_and_parse_webhook(self, payload: bytes, signature: str | None) -> WebhookEvent:
        if self.webhook_secret and signature:
            stripe = self._client()
            try:
                event = stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
            except Exception as exc:  # noqa: BLE001
                raise GatewayError(f"Invalid Stripe signature: {exc}") from exc
        else:
            # Without a secret we still parse (dev only) but cannot verify.
            event = json.loads(payload.decode("utf-8"))

        etype = event.get("type", "")
        obj = event.get("data", {}).get("object", {})
        return WebhookEvent(
            event_id=event.get("id", ""),
            event_type=etype,
            gateway_subscription_id=obj.get("subscription") or obj.get("id"),
            gateway_customer_id=obj.get("customer"),
            gateway_payment_id=obj.get("payment_intent") or obj.get("id"),
            amount_cents=obj.get("amount_paid") or obj.get("amount_total") or obj.get("amount"),
            currency=(obj.get("currency") or "usd").upper(),
            status=_map_status(etype),
            raw=event,
        )

    async def refund(self, gateway_payment_id: str, *, amount_cents: int | None = None) -> bool:
        if not self.is_configured:
            return False
        stripe = self._client()
        try:
            params = {"payment_intent": gateway_payment_id}
            if amount_cents:
                params["amount"] = amount_cents
            stripe.Refund.create(**params)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("stripe_refund_failed", error=str(exc))
            return False


def _map_status(event_type: str) -> str | None:
    return {
        "checkout.session.completed": "succeeded",
        "invoice.paid": "succeeded",
        "invoice.payment_succeeded": "succeeded",
        "invoice.payment_failed": "failed",
        "customer.subscription.deleted": "canceled",
        "customer.subscription.updated": "updated",
    }.get(event_type)
