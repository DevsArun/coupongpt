"""Razorpay gateway implementation (lazy SDK import)."""
from __future__ import annotations

import hashlib
import hmac
import json

from app.billing.base import CheckoutResult, GatewayError, PaymentGateway, WebhookEvent
from app.core.logging import get_logger

logger = get_logger("billing.razorpay")


class RazorpayGateway(PaymentGateway):
    slug = "razorpay"

    def _client(self):
        try:
            import razorpay
        except ImportError as exc:  # pragma: no cover
            raise GatewayError("razorpay SDK is not installed") from exc
        return razorpay.Client(auth=(self.api_key, self.secret))

    async def create_checkout(self, *, plan, user, success_url: str, cancel_url: str) -> CheckoutResult:
        if not self.is_configured or not plan.razorpay_plan_id:
            return CheckoutResult(gateway=self.slug, mode="demo")

        client = self._client()
        try:
            total_count = 12 if plan.billing_period == "month" else 1
            sub = client.subscription.create(
                {
                    "plan_id": plan.razorpay_plan_id,
                    "total_count": total_count,
                    "customer_notify": 1,
                    "notes": {"user_id": str(user.id), "plan_slug": plan.slug},
                }
            )
        except Exception as exc:  # noqa: BLE001
            raise GatewayError(f"Razorpay subscription failed: {exc}") from exc

        return CheckoutResult(
            gateway=self.slug,
            mode="redirect",
            gateway_subscription_id=sub.get("id"),
            checkout_url=sub.get("short_url"),
            client_payload={"subscription_id": sub.get("id"), "key_id": self.api_key},
        )

    def verify_and_parse_webhook(self, payload: bytes, signature: str | None) -> WebhookEvent:
        if self.webhook_secret and signature:
            expected = hmac.new(
                self.webhook_secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise GatewayError("Invalid Razorpay signature")

        event = json.loads(payload.decode("utf-8"))
        etype = event.get("event", "")
        entity = (
            event.get("payload", {}).get("subscription", {}).get("entity")
            or event.get("payload", {}).get("payment", {}).get("entity")
            or {}
        )
        return WebhookEvent(
            event_id=event.get("id", "") or entity.get("id", ""),
            event_type=etype,
            gateway_subscription_id=entity.get("subscription_id") or entity.get("id"),
            gateway_customer_id=entity.get("customer_id"),
            gateway_payment_id=entity.get("id"),
            amount_cents=entity.get("amount"),
            currency=(entity.get("currency") or "INR"),
            status=_map_status(etype),
            raw=event,
        )

    async def refund(self, gateway_payment_id: str, *, amount_cents: int | None = None) -> bool:
        if not self.is_configured:
            return False
        client = self._client()
        try:
            params = {}
            if amount_cents:
                params["amount"] = amount_cents
            client.payment.refund(gateway_payment_id, params)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("razorpay_refund_failed", error=str(exc))
            return False


def _map_status(event_type: str) -> str | None:
    return {
        "subscription.activated": "succeeded",
        "subscription.charged": "succeeded",
        "payment.captured": "succeeded",
        "payment.failed": "failed",
        "subscription.cancelled": "canceled",
        "subscription.completed": "canceled",
    }.get(event_type)
