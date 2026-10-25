from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from tests.helpers import register
from zooffer.config import settings
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    PaymentEvent,
    PaymentOrder,
    Plan,
    Subscription,
    User,
)
from zooffer.main import app
from zooffer.services.payments import FakePaymentProvider


@asynccontextmanager
async def extra_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


async def _plan(db, *, code: str = "plus", price: int = 39900) -> Plan:
    plan = Plan(
        id=uuid4(),
        code=code,
        name="Zooffer Плюс",
        description="Больше возможностей",
        price_kopecks=price,
        currency="RUB",
        stars_amount=None,
        period_days=30,
        entitlements=["unlimited_swipes", "undo"],
        is_active=True,
        sort_order=1,
        is_placeholder_price=False,
    )
    db.add(plan)
    await db.commit()
    return plan


async def _set_role(db, public_id: str, role: str) -> None:
    user = await db.scalar(select(User).where(User.public_id == UUID(public_id)))
    assert user is not None
    user.role = role
    await db.commit()


async def _create_paid_order(client: AsyncClient, plan_code: str) -> dict:
    created = await client.post("/api/v1/billing/orders", json={"plan_code": plan_code})
    assert created.status_code == 201, created.text
    order = created.json()
    confirmed = await client.post(f"/api/v1/billing/orders/{order['public_id']}/demo-confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "paid"
    return confirmed.json()


async def test_order_creation_demo_confirmation_and_idempotency(client: AsyncClient, db) -> None:
    await register(client, "buyer@example.com")
    await _plan(db)

    subscription = await client.get("/api/v1/billing/subscription")
    assert subscription.status_code == 200
    assert subscription.json()["payments_available"] is True
    assert subscription.json()["payments_demo"] is True

    created = await client.post("/api/v1/billing/orders", json={"plan_code": "plus"})
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["amount_kopecks"] == 39900
    assert order["currency"] == "RUB"
    assert order["demo"] is True
    assert order["status"] in {"created", "pending"}
    assert order["confirmation_url"]

    # The same plan reuses a fresh order instead of creating duplicates.
    reused = await client.post("/api/v1/billing/orders", json={"plan_code": "plus"})
    assert reused.status_code == 201
    assert reused.json()["public_id"] == order["public_id"]

    confirmed = await client.post(f"/api/v1/billing/orders/{order['public_id']}/demo-confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "paid"

    again = await client.post(f"/api/v1/billing/orders/{order['public_id']}/demo-confirm")
    assert again.status_code == 200
    assert again.json()["status"] == "paid"

    current = await client.get("/api/v1/billing/subscription")
    body = current.json()
    assert body["status"] == "active"
    assert body["plan_code"] == "plus"
    assert body["entitlements"] == ["undo", "unlimited_swipes"]

    db.expire_all()
    event_count = await db.scalar(
        select(func.count())
        .select_from(PaymentEvent)
        .where(PaymentEvent.order_id == UUID(order["public_id"]))
    )
    assert event_count == 1
    subscriptions = (
        await db.scalars(select(Subscription).where(Subscription.status == "active"))
    ).all()
    assert len(subscriptions) == 1
    subscription_id = subscriptions[0].id

    # A second purchase extends the paid period rather than shortening it.
    paid = await _create_paid_order(client, "plus")
    assert paid["plan_code"] == "plus"
    db.expire_all()
    refreshed = await db.get(Subscription, subscription_id)
    assert refreshed is not None
    assert refreshed.current_period_end is not None
    assert refreshed.current_period_end > utcnow()


async def test_webhook_signature_amount_and_order_ownership(client: AsyncClient, db) -> None:
    await register(client, "webhook@example.com")
    await _plan(db)
    created = await client.post("/api/v1/billing/orders", json={"plan_code": "plus"})
    order = created.json()
    order_id = UUID(order["public_id"])

    db.expire_all()
    stored = await db.get(PaymentOrder, order_id)
    assert stored is not None
    assert stored.provider_payment_id is not None
    payment_id = stored.provider_payment_id
    amount_kopecks = stored.amount_kopecks
    currency = stored.currency
    provider = FakePaymentProvider()

    bad_headers, bad_body = provider.signed_success_webhook(
        order_id=order_id,
        provider_payment_id=payment_id,
        amount_kopecks=amount_kopecks,
        currency=currency,
    )
    bad_headers["X-Fake-Signature"] = "00" * 32
    bad = await client.post("/api/v1/billing/webhooks/fake", content=bad_body, headers=bad_headers)
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_signature"

    # Amount mismatch is recorded under the provider event id, so use a second
    # order to prove validation without poisoning the valid first event.
    await _plan(db, code="premium", price=99900)
    other_order = (
        await client.post("/api/v1/billing/orders", json={"plan_code": "premium"})
    ).json()
    db.expire_all()
    stored_other = await db.get(PaymentOrder, UUID(other_order["public_id"]))
    assert stored_other is not None
    assert stored_other.provider_payment_id is not None
    mismatch_headers, mismatch_body = provider.signed_success_webhook(
        order_id=stored_other.id,
        provider_payment_id=stored_other.provider_payment_id,
        amount_kopecks=1,
        currency=stored_other.currency,
    )
    mismatch = await client.post(
        "/api/v1/billing/webhooks/fake", content=mismatch_body, headers=mismatch_headers
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "amount_mismatch"

    async with extra_client() as other:
        await register(other, "intruder@example.com")
        foreign = await other.get(f"/api/v1/billing/orders/{order['public_id']}")
        assert foreign.status_code == 404
        assert foreign.json()["error"]["code"] == "order_not_found"

    # A valid, correctly priced event succeeds.
    headers, body = provider.signed_success_webhook(
        order_id=order_id,
        provider_payment_id=payment_id,
        amount_kopecks=amount_kopecks,
        currency=currency,
    )
    ok = await client.post("/api/v1/billing/webhooks/fake", content=body, headers=headers)
    assert ok.status_code == 200, ok.text
    assert ok.json()["result"] == "paid"

    duplicate = await client.post("/api/v1/billing/webhooks/fake", content=body, headers=headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["result"] == "duplicate"

    refund_headers, refund_body = provider.signed_refund_webhook(
        order_id=order_id,
        provider_payment_id=payment_id,
        amount_kopecks=amount_kopecks,
        currency=currency,
    )
    refunded = await client.post(
        "/api/v1/billing/webhooks/fake", content=refund_body, headers=refund_headers
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["result"] == "refunded"

    current = await client.get("/api/v1/billing/subscription")
    assert current.json()["status"] in {"expired", "canceled"}
    assert current.json()["entitlements"] == []


async def test_payments_unavailable_and_plan_validation(
    client: AsyncClient, db, monkeypatch
) -> None:
    await register(client, "blocked@example.com")
    await _plan(db)
    monkeypatch.setattr(settings, "payment_provider", "yookassa")
    monkeypatch.setattr(settings, "yookassa_shop_id", "")
    monkeypatch.setattr(settings, "yookassa_secret_key", "")

    response = await client.post("/api/v1/billing/orders", json={"plan_code": "plus"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "payments_unavailable"

    view = await client.get("/api/v1/billing/subscription")
    assert view.json()["payments_available"] is False
    assert view.json()["payments_demo"] is False

    unknown = await client.post("/api/v1/billing/orders", json={"plan_code": "missing"})
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "payments_unavailable"

    monkeypatch.setattr(settings, "payment_provider", "fake")
    missing = await client.post("/api/v1/billing/orders", json={"plan_code": "missing"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "plan_not_found"


async def test_admin_payment_detail_refund_grant_and_reconcile(client: AsyncClient, db) -> None:
    await register(client, "admin-pay@example.com")
    plan = await _plan(db)
    plan_id = plan.id
    paid = await _create_paid_order(client, "plus")

    setup = await client.post("/api/v1/auth/mfa/setup")
    secret = setup.json()["secret"]
    confirmed = await client.post(
        "/api/v1/auth/mfa/confirm", json={"code": pyotp.TOTP(secret).now()}
    )
    assert confirmed.status_code == 200
    me = await client.get("/api/v1/auth/me")
    await _set_role(db, me.json()["user"]["public_id"], "superadmin")

    detail = await client.get(f"/api/v1/admin/payments/{paid['public_id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["order"]["status"] == "paid"
    assert len(detail.json()["events"]) == 1
    assert detail.json()["events"][0]["signature_valid"] is True

    reconcile = await client.get("/api/v1/admin/payments-reconcile")
    assert reconcile.status_code == 200, reconcile.text
    assert reconcile.json()["paid_orders"] == 1
    assert reconcile.json()["active_subscriptions"] == 1
    assert reconcile.json()["paid_without_subscription"] == 0

    refund = await client.post(
        f"/api/v1/admin/payments/{paid['public_id']}/refund",
        json={"reason": "Проверка возврата в тесте"},
    )
    assert refund.status_code == 200, refund.text
    assert refund.json()["order"]["status"] == "refunded"

    current = await client.get("/api/v1/billing/subscription")
    assert current.json()["status"] in {"expired", "canceled"}
    db.expire_all()
    subscription = await db.scalar(select(Subscription).where(Subscription.plan_id == plan_id))
    assert subscription is not None
    assert subscription.status == "canceled"

    admin_public_id = me.json()["user"]["public_id"]

    grant = await client.post(
        f"/api/v1/admin/users/{admin_public_id}/entitlements",
        json={"code": "see_who_liked", "days": 10},
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["code"] == "see_who_liked"
    assert grant.json()["expires_at"] is not None

    invalid = await client.post(
        f"/api/v1/admin/users/{admin_public_id}/entitlements",
        json={"code": "not_a_real_entitlement", "days": 10},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "unknown_entitlement"

    revoke = await client.delete(
        f"/api/v1/admin/users/{admin_public_id}/entitlements/see_who_liked"
    )
    assert revoke.status_code == 200
    assert revoke.json()["ok"] is True

    missing = await client.delete(
        f"/api/v1/admin/users/{admin_public_id}/entitlements/see_who_liked"
    )
    assert missing.status_code == 404


@pytest.mark.parametrize("command", ["refund"])
async def test_demo_confirm_requires_fake_mode_and_ownership(
    client: AsyncClient, db, monkeypatch, command: str
) -> None:
    del command
    await register(client, "demo-mode@example.com")
    await _plan(db)
    created = await client.post("/api/v1/billing/orders", json={"plan_code": "plus"})
    order = created.json()

    async with extra_client() as other:
        await register(other, "demo-other@example.com")
        foreign = await other.post(f"/api/v1/billing/orders/{order['public_id']}/demo-confirm")
        assert foreign.status_code == 404

    monkeypatch.setattr(settings, "payment_provider", "yookassa")
    monkeypatch.setattr(settings, "yookassa_shop_id", "shop")
    monkeypatch.setattr(settings, "yookassa_secret_key", "secret")
    denied = await client.post(f"/api/v1/billing/orders/{order['public_id']}/demo-confirm")
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "demo_payment_unavailable"
