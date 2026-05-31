"""Payment gateway abstraction.

A single ``PaymentGateway`` interface lets the billing service treat Stripe and
Razorpay uniformly. Each gateway:
  * creates a checkout (subscription) session/order,
  * verifies and parses incoming webhooks into normalized events,
  * issues refunds.

When a gateway has no API key configured the system runs in **demo mode** — the
billing service activates the subscription directly so the product is fully
usable for local development and demos without real payment credentials.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


class GatewayError(Exception):
    pass


@dataclass
class CheckoutResult:
    gateway: str
    mode: str  # "redirect" (hosted checkout) | "demo" (activated immediately)
    checkout_url: str | None = None
    gateway_subscription_id: str | None = None
    gateway_customer_id: str | None = None
    client_payload: dict[str, Any] | None = None  # for client-side SDK flows


@dataclass
class WebhookEvent:
    event_id: str
    event_type: str
    # Normalized fields extracted from the provider payload:
    gateway_subscription_id: str | None = None
    gateway_customer_id: str | None = None
    gateway_payment_id: str | None = None
    amount_cents: int | None = None
    currency: str | None = None
    status: str | None = None  # succeeded|failed|canceled|...
    raw: dict[str, Any] | None = None


class PaymentGateway(abc.ABC):
    slug: str = "base"

    def __init__(self, *, api_key: str = "", secret: str = "", webhook_secret: str = "") -> None:
        self.api_key = api_key
        self.secret = secret
        self.webhook_secret = webhook_secret

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key or self.secret)

    @abc.abstractmethod
    async def create_checkout(
        self, *, plan, user, success_url: str, cancel_url: str
    ) -> CheckoutResult:
        ...

    @abc.abstractmethod
    def verify_and_parse_webhook(self, payload: bytes, signature: str | None) -> WebhookEvent:
        ...

    @abc.abstractmethod
    async def refund(self, gateway_payment_id: str, *, amount_cents: int | None = None) -> bool:
        ...
