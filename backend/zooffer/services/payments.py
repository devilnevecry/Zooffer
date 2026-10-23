"""Payment provider adapters.

Only the fake provider is exercised end-to-end in this repository because no
merchant credentials are available. The YooKassa adapter is written against the
documented HTTP API but remains ``IMPLEMENTED-UNVERIFIED`` and ``BLOCKED`` for a
real sandbox run (see ``docs/PAYMENTS.md`` and ``docs/BLOCKERS.md``).

Security rules followed here:

* card data never reaches this application;
* prices are computed by the backend, not supplied by a client;
* the fake provider signs every simulated webhook with the server pepper;
* YooKassa notifications are not trusted on their own: the billing service
  re-fetches the payment from the provider API before changing an order.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx

from zooffer.config import settings
from zooffer.core.errors import AppError


class PaymentProviderError(AppError):
    status_code = 502
    code = "payment_provider_error"


class PaymentProviderNotConfigured(PaymentProviderError):
    status_code = 503
    code = "payment_provider_not_configured"


class PaymentWebhookError(AppError):
    status_code = 400
    code = "invalid_payment_webhook"


@dataclass(frozen=True, slots=True)
class PaymentIntent:
    provider_payment_id: str
    status: str
    confirmation_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerifiedEvent:
    provider_event_id: str
    event_type: str
    provider_payment_id: str | None
    status: str
    order_id: UUID | None = None
    amount_kopecks: int | None = None
    currency: str | None = None
    provider_subscription_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    signature_valid: bool = False


@dataclass(frozen=True, slots=True)
class ProviderState:
    provider_payment_id: str
    status: str
    amount_kopecks: int | None = None
    currency: str | None = None
    paid: bool = False
    provider_subscription_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(Protocol):
    name: str

    async def create_payment(
        self,
        *,
        order_id: UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> PaymentIntent: ...

    async def verify_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> VerifiedEvent: ...

    async def fetch_payment(self, provider_payment_id: str) -> ProviderState: ...

    async def refund(
        self, provider_payment_id: str, amount_kopecks: int, idempotency_key: str
    ) -> str: ...


def _parse_uuid(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _money(kopecks: int) -> str:
    return f"{kopecks / 100:.2f}"


class FakePaymentProvider:
    """Deterministic, locally testable provider.

    It is only selected in development/test environments. The simulated webhook
    uses the same verification and processing path as a real provider so the
    order -> event -> entitlement flow is genuinely exercised.
    """

    name = "fake"

    def _secret(self) -> bytes:
        return settings.secret_pepper.encode("utf-8")

    async def create_payment(
        self,
        *,
        order_id: UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> PaymentIntent:
        del amount_kopecks, currency, description, idempotency_key, metadata
        provider_payment_id = f"fake-{uuid4().hex}"
        # The demo checkout page clearly labels this as a simulated payment.
        return PaymentIntent(
            provider_payment_id=provider_payment_id,
            status="pending",
            confirmation_url=return_url,
            raw={
                "id": provider_payment_id,
                "order_id": str(order_id),
                "status": "pending",
                "provider": self.name,
            },
        )

    def signed_success_webhook(
        self,
        *,
        order_id: UUID,
        provider_payment_id: str,
        amount_kopecks: int,
        currency: str,
    ) -> tuple[dict[str, str], bytes]:
        payload = {
            "event_id": f"fake:payment.succeeded:{provider_payment_id}",
            "type": "payment.succeeded",
            "payment_id": provider_payment_id,
            "order_id": str(order_id),
            "status": "succeeded",
            "amount_kopecks": amount_kopecks,
            "currency": currency,
        }
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self._secret(), raw, hashlib.sha256).hexdigest()
        return {"X-Fake-Signature": signature}, raw

    def signed_refund_webhook(
        self,
        *,
        order_id: UUID,
        provider_payment_id: str,
        amount_kopecks: int,
        currency: str,
    ) -> tuple[dict[str, str], bytes]:
        payload = {
            "event_id": f"fake:refund.succeeded:{provider_payment_id}",
            "type": "refund.succeeded",
            "payment_id": provider_payment_id,
            "order_id": str(order_id),
            "status": "refunded",
            "amount_kopecks": amount_kopecks,
            "currency": currency,
        }
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self._secret(), raw, hashlib.sha256).hexdigest()
        return {"X-Fake-Signature": signature}, raw

    async def verify_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> VerifiedEvent:
        received = headers.get("x-fake-signature", "")
        expected = hmac.new(self._secret(), body, hashlib.sha256).hexdigest()
        if not received or not hmac.compare_digest(received, expected):
            raise PaymentWebhookError("Invalid fake payment signature", code="invalid_signature")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise PaymentWebhookError("Malformed payment payload", code="invalid_payload") from exc
        if not isinstance(payload, dict):
            raise PaymentWebhookError("Malformed payment payload", code="invalid_payload")
        event_id = str(payload.get("event_id") or "").strip()
        event_type = str(payload.get("type") or "").strip()
        payment_id = str(payload.get("payment_id") or "").strip()
        status = str(payload.get("status") or "").strip().lower()
        if not event_id or not event_type or not payment_id or not status:
            raise PaymentWebhookError("Incomplete payment payload", code="invalid_payload")
        amount = payload.get("amount_kopecks")
        try:
            amount_kopecks = int(amount) if amount is not None else None
        except (TypeError, ValueError) as exc:
            raise PaymentWebhookError("Invalid amount", code="invalid_amount") from exc
        currency = str(payload.get("currency") or "").upper() or None
        return VerifiedEvent(
            provider_event_id=event_id,
            event_type=event_type,
            provider_payment_id=payment_id,
            status=status,
            order_id=_parse_uuid(payload.get("order_id")),
            amount_kopecks=amount_kopecks,
            currency=currency,
            payload=payload,
            signature_valid=True,
        )

    async def fetch_payment(self, provider_payment_id: str) -> ProviderState:
        raise PaymentProviderError(
            "The fake provider confirms payments through signed local webhooks only.",
            code="fake_fetch_not_supported",
        )

    async def refund(
        self, provider_payment_id: str, amount_kopecks: int, idempotency_key: str
    ) -> str:
        del amount_kopecks, idempotency_key
        return f"fake-refund-{provider_payment_id}-{uuid4().hex[:12]}"


class YooKassaProvider:
    """YooKassa adapter. Requires merchant credentials and a sandbox run.

    The notification endpoint itself is not signed by YooKassa. The safe pattern
    (and the one used by the billing service) is to treat the notification only as
    a trigger and re-fetch the payment with authenticated API credentials before
    changing local state. Merchant IP allow-listing should additionally be
    configured at the reverse proxy in production.
    """

    name = "yookassa"
    api_base = "https://api.yookassa.ru/v3"

    def __init__(
        self,
        *,
        shop_id: str | None = None,
        secret_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.shop_id = shop_id or settings.yookassa_shop_id
        self.secret_key = secret_key or settings.yookassa_secret_key
        self._transport = transport
        if not self.shop_id or not self.secret_key:
            raise PaymentProviderNotConfigured(
                "YooKassa credentials are not configured", code="yookassa_not_configured"
            )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.api_base,
            auth=(self.shop_id, self.secret_key),
            timeout=15,
            transport=self._transport,
            headers={"Accept": "application/json"},
        )

    async def create_payment(
        self,
        *,
        order_id: UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        idempotency_key: str,
        metadata: dict[str, str],
    ) -> PaymentIntent:
        payload = {
            "amount": {"value": _money(amount_kopecks), "currency": currency},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": description[:128],
            "metadata": {**metadata, "order_id": str(order_id)},
        }
        try:
            async with self._client() as client:
                response = await client.post(
                    "/payments",
                    json=payload,
                    headers={"Idempotence-Key": idempotency_key},
                )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                "YooKassa rejected the payment request", code="payment_create_failed"
            ) from exc
        return PaymentIntent(
            provider_payment_id=str(data["id"]),
            status=str(data.get("status") or "pending"),
            confirmation_url=(data.get("confirmation") or {}).get("confirmation_url"),
            raw=data,
        )

    async def verify_webhook(
        self, headers: dict[str, str], body: bytes
    ) -> VerifiedEvent:
        del headers
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise PaymentWebhookError(
                "Malformed YooKassa notification", code="invalid_payload"
            ) from exc
        if not isinstance(payload, dict):
            raise PaymentWebhookError("Malformed YooKassa notification", code="invalid_payload")
        event_type = str(payload.get("event") or "").strip()
        obj = payload.get("object")
        if not event_type or not isinstance(obj, dict):
            raise PaymentWebhookError("Incomplete YooKassa notification", code="invalid_payload")
        payment_id = str(obj.get("id") or "").strip()
        status = str(obj.get("status") or "").strip().lower()
        if not payment_id:
            raise PaymentWebhookError("Missing YooKassa payment id", code="invalid_payload")
        if event_type.startswith("refund."):
            payment_id = str(obj.get("payment_id") or payment_id)
            status = "refunded"
        metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
        amount = obj.get("amount") if isinstance(obj.get("amount"), dict) else {}
        try:
            amount_kopecks = (
                round(float(amount.get("value")) * 100) if amount.get("value") else None
            )
        except (TypeError, ValueError):
            amount_kopecks = None
        return VerifiedEvent(
            provider_event_id=f"{event_type}:{payment_id}:{status}",
            event_type=event_type,
            provider_payment_id=payment_id,
            status=status,
            order_id=_parse_uuid(metadata.get("order_id")),
            amount_kopecks=amount_kopecks,
            currency=str(amount.get("currency") or "").upper() or None,
            payload=payload,
            # Verified only after fetch_payment() succeeds in the billing service.
            signature_valid=False,
        )

    async def fetch_payment(self, provider_payment_id: str) -> ProviderState:
        try:
            async with self._client() as client:
                response = await client.get(f"/payments/{provider_payment_id}")
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                "Could not verify the YooKassa payment", code="payment_fetch_failed"
            ) from exc
        amount = data.get("amount") if isinstance(data.get("amount"), dict) else {}
        try:
            amount_kopecks = (
                round(float(amount.get("value")) * 100) if amount.get("value") else None
            )
        except (TypeError, ValueError):
            amount_kopecks = None
        status = str(data.get("status") or "pending").lower()
        return ProviderState(
            provider_payment_id=str(data["id"]),
            status=status,
            amount_kopecks=amount_kopecks,
            currency=str(amount.get("currency") or "").upper() or None,
            paid=status == "succeeded",
            provider_subscription_id=None,
            raw=data,
        )

    async def refund(
        self, provider_payment_id: str, amount_kopecks: int, idempotency_key: str
    ) -> str:
        payload = {
            "payment_id": provider_payment_id,
            "amount": {"value": _money(amount_kopecks), "currency": "RUB"},
        }
        try:
            async with self._client() as client:
                response = await client.post(
                    "/refunds",
                    json=payload,
                    headers={"Idempotence-Key": idempotency_key},
                )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise PaymentProviderError(
                "YooKassa rejected the refund", code="refund_failed"
            ) from exc
        return str(data["id"])


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    selected = (name or settings.payment_provider).lower()
    configured = settings.payment_provider.lower()
    if selected != configured:
        raise PaymentProviderNotConfigured(
            "This payment provider is not enabled", code="provider_not_enabled"
        )
    if selected == "fake":
        if settings.is_production:
            raise PaymentProviderNotConfigured(
                "The fake provider is disabled in production", code="fake_disabled"
            )
        return FakePaymentProvider()
    if selected == "yookassa":
        return YooKassaProvider()
    raise PaymentProviderNotConfigured("Unknown payment provider", code="unknown_provider")
