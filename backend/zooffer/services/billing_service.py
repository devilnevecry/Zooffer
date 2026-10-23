from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.config import settings
from zooffer.core.enums import Entitlement
from zooffer.core.errors import NotFoundError, ValidationAppError
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    AuditLog,
    EntitlementGrant,
    PaymentEvent,
    PaymentOrder,
    Plan,
    Refund,
    Subscription,
    User,
)
from zooffer.schemas.account import SubscriptionView
from zooffer.schemas.billing import (
    AdminPaymentDetailView,
    AdminPaymentEventView,
    BillingOrderView,
)
from zooffer.services import notification_service, quota_service
from zooffer.services.entitlements import get_entitlements
from zooffer.services.payments import (
    FakePaymentProvider,
    PaymentProviderNotConfigured,
    VerifiedEvent,
    get_payment_provider,
)

logger = logging.getLogger("zooffer.billing")

ORDER_TTL_MINUTES = 30
REUSE_ORDER_MINUTES = 15


def payment_mode() -> str:
    if settings.payment_provider == "yookassa":
        return (
            "live"
            if settings.yookassa_shop_id and settings.yookassa_secret_key
            else "unavailable"
        )
    if settings.payment_provider == "fake" and settings.environment in {"dev", "test"}:
        return "demo"
    return "unavailable"


def payments_available() -> bool:
    return payment_mode() != "unavailable"


def payments_demo() -> bool:
    return payment_mode() == "demo"


def _plan_query():  # type: ignore[no-untyped-def]
    return select(Plan).where(Plan.is_active.is_(True))


async def _plan(db: AsyncSession, plan_code: str) -> Plan:
    plan = await db.scalar(_plan_query().where(Plan.code == plan_code))
    if plan is None:
        raise NotFoundError("Тариф не найден", code="plan_not_found")
    return plan


def _return_url(order_id: UUID) -> str:
    base = settings.app_base_url.rstrip("/")
    if settings.payment_provider == "yookassa" and settings.yookassa_return_url:
        return settings.yookassa_return_url
    return f"{base}/account/subscription/checkout?order={order_id}"


async def create_order(
    db: AsyncSession, user: User, plan_code: str
) -> BillingOrderView:
    if not payments_available():
        raise ValidationAppError(
            "Онлайн-оплата пока недоступна. Попробуйте позже или напишите в поддержку.",
            code="payments_unavailable",
        )
    plan = await _plan(db, plan_code)
    if plan.price_kopecks <= 0:
        raise ValidationAppError(
            "Этот тариф не требует оплаты", code="free_plan_not_purchasable"
        )
    if settings.is_production and plan.is_placeholder_price:
        raise ValidationAppError(
            "Цена тарифа ещё не утверждена. Оплата временно недоступна.",
            code="placeholder_price",
        )
    now = utcnow()
    recent = await db.scalar(
        select(PaymentOrder)
        .where(
            PaymentOrder.user_id == user.id,
            PaymentOrder.plan_id == plan.id,
            PaymentOrder.status.in_(["created", "pending"]),
            PaymentOrder.created_at >= now - timedelta(minutes=REUSE_ORDER_MINUTES),
            PaymentOrder.confirmation_url.is_not(None),
        )
        .order_by(PaymentOrder.created_at.desc())
        .limit(1)
    )
    if recent is not None:
        return await order_view(db, recent)

    provider = get_payment_provider()
    order_id = uuid4()
    provider_payment_id = ""
    confirmation_url: str | None = None
    status = "created"
    raw: dict[str, Any] | None = None
    try:
        intent = await provider.create_payment(
            order_id=order_id,
            amount_kopecks=plan.price_kopecks,
            currency=plan.currency,
            description=f"Zooffer: {plan.name}",
            return_url=_return_url(order_id),
            idempotency_key=str(order_id),
            metadata={"plan_code": plan.code, "user_public_id": str(user.public_id)},
        )
        provider_payment_id = intent.provider_payment_id
        confirmation_url = intent.confirmation_url
        status = "pending" if intent.status in {"pending", "created"} else intent.status
        raw = intent.raw
    except PaymentProviderNotConfigured as exc:
        logger.warning("payment_provider_not_configured", exc_info=exc)
        raise ValidationAppError(
            "Онлайн-оплата пока недоступна. Попробуйте позже.",
            code="payments_unavailable",
        ) from exc
    except Exception as exc:  # provider errors are logged without payload details
        logger.exception("payment_create_failed")
        raise ValidationAppError(
            "Не удалось создать платёж. Попробуйте ещё раз позже.",
            code="payment_create_failed",
        ) from exc

    order = PaymentOrder(
        id=order_id,
        user_id=user.id,
        plan_id=plan.id,
        provider=provider.name,
        provider_payment_id=provider_payment_id,
        idempotency_key=str(order_id),
        amount_kopecks=plan.price_kopecks,
        currency=plan.currency,
        stars_amount=plan.stars_amount,
        status=status,
        confirmation_url=confirmation_url,
        expires_at=now + timedelta(minutes=ORDER_TTL_MINUTES),
        raw_metadata=raw,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return await order_view(db, order)


async def list_orders(db: AsyncSession, user: User) -> list[BillingOrderView]:
    rows = (
        await db.scalars(
            select(PaymentOrder)
            .where(PaymentOrder.user_id == user.id)
            .order_by(PaymentOrder.created_at.desc())
            .limit(50)
        )
    ).all()
    return [await order_view(db, row) for row in rows]


async def get_order(db: AsyncSession, user: User, order_id: UUID) -> BillingOrderView:
    order = await db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.id == order_id, PaymentOrder.user_id == user.id
        )
    )
    if order is None:
        raise NotFoundError("Платёж не найден", code="order_not_found")
    return await order_view(db, order)


async def order_view(db: AsyncSession, order: PaymentOrder) -> BillingOrderView:
    plan = await db.get(Plan, order.plan_id)
    return BillingOrderView(
        public_id=order.id,
        plan_code=plan.code if plan else "unknown",
        provider=order.provider,
        status=order.status,
        amount_kopecks=order.amount_kopecks,
        currency=order.currency,
        confirmation_url=order.confirmation_url,
        demo=payments_demo(),
        created_at=order.created_at,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
    )


async def subscription_view(db: AsyncSession, user: User) -> SubscriptionView:
    now = utcnow()
    row = (
        await db.execute(
            select(Subscription, Plan)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
    ).first()
    entitlements = sorted(await get_entitlements(db, user.id))
    quota = await quota_service.get_quota(db, user.id)
    available = payments_available()
    if row is None:
        return SubscriptionView(
            status="none",
            entitlements=entitlements,
            quota_limit=quota.limit,
            quota_unlimited=quota.unlimited,
            payments_available=available,
            payments_demo=payments_demo(),
            payment_provider=settings.payment_provider,
        )
    subscription, plan = row
    active = (
        subscription.status in {"active", "past_due"}
        and subscription.current_period_end is not None
        and subscription.current_period_end > now
    )
    return SubscriptionView(
        status=subscription.status if active else "expired",
        plan_code=plan.code,
        plan_name=plan.name,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        entitlements=entitlements,
        quota_limit=quota.limit,
        quota_unlimited=quota.unlimited,
        payments_available=available,
        payments_demo=payments_demo(),
        payment_provider=settings.payment_provider,
    )


async def cancel_subscription(db: AsyncSession, user: User) -> SubscriptionView:
    subscription = await db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status.in_(["active", "past_due"]),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    if subscription is None:
        raise ValidationAppError(
            "Активной подписки нет", code="subscription_not_found"
        )
    subscription.cancel_at_period_end = True
    subscription.canceled_at = utcnow()
    await db.commit()
    return await subscription_view(db, user)


async def _record_event(
    db: AsyncSession,
    *,
    provider: str,
    event: VerifiedEvent,
    order_id: UUID | None,
    signature_valid: bool,
) -> UUID | None:
    statement = (
        pg_insert(PaymentEvent)
        .values(
            id=uuid4(),
            provider=provider,
            provider_event_id=event.provider_event_id,
            order_id=order_id,
            event_type=event.event_type,
            signature_valid=signature_valid,
            payload=event.payload,
        )
        .on_conflict_do_nothing(
            index_elements=[PaymentEvent.provider, PaymentEvent.provider_event_id]
        )
        .returning(PaymentEvent.id)
    )
    return await db.scalar(statement)


async def _mark_event_error(
    db: AsyncSession, event_id: UUID, message: str
) -> None:
    event_row = await db.get(PaymentEvent, event_id)
    if event_row is not None:
        event_row.error = message[:500]
        event_row.processed_at = utcnow()


async def _activate_subscription(
    db: AsyncSession,
    *,
    order: PaymentOrder,
    plan: Plan,
    event: VerifiedEvent,
) -> Subscription:
    now = utcnow()
    subscription = await db.scalar(
        select(Subscription)
        .where(Subscription.user_id == order.user_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    base = now
    if (
        subscription is not None
        and subscription.status in {"active", "past_due"}
        and subscription.current_period_end is not None
        and subscription.current_period_end > now
    ):
        base = subscription.current_period_end
    if subscription is None:
        subscription = Subscription(
            id=uuid4(),
            user_id=order.user_id,
            plan_id=plan.id,
            status="active",
            provider=order.provider,
            provider_subscription_id=event.provider_subscription_id,
            current_period_start=now,
            current_period_end=base + timedelta(days=plan.period_days),
        )
        db.add(subscription)
    else:
        subscription.plan_id = plan.id
        subscription.status = "active"
        subscription.provider = order.provider
        subscription.provider_subscription_id = (
            event.provider_subscription_id or subscription.provider_subscription_id
        )
        subscription.current_period_start = (
            subscription.current_period_start
            if subscription.current_period_end is not None
            and subscription.current_period_end > now
            else now
        )
        subscription.current_period_end = base + timedelta(days=plan.period_days)
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.grace_until = None
    notification_service.create_notification(
        db,
        order.user_id,
        category="subscriptions",
        title="Подписка активирована",
        body=(
            f"Тариф «{plan.name}» действует до "
            f"{subscription.current_period_end:%d.%m.%Y}."
        ),
        data={"order_id": str(order.id)},
    )
    return subscription


async def _revoke_subscription(
    db: AsyncSession, user_id: UUID, *, reason: str
) -> None:
    subscription = await db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "past_due"]),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if subscription is None:
        return
    now = utcnow()
    subscription.status = "canceled"
    subscription.cancel_at_period_end = True
    subscription.canceled_at = now
    subscription.current_period_end = now
    notification_service.create_notification(
        db,
        user_id,
        category="subscriptions",
        title="Подписка завершена",
        body=reason[:600],
    )


async def process_webhook(
    db: AsyncSession,
    provider_name: str,
    headers: dict[str, str],
    body: bytes,
) -> str:
    provider = get_payment_provider(provider_name)
    normalized = {key.lower(): value for key, value in headers.items()}
    event = await provider.verify_webhook(normalized, body)

    # YooKassa notifications are unsigned. Re-fetching with merchant credentials
    # makes the provider API the source of truth for amount/status.
    if provider.name == "yookassa" and event.provider_payment_id:
        state = await provider.fetch_payment(event.provider_payment_id)
        event = replace(
            event,
            status="refunded" if event.event_type.startswith("refund.") else state.status,
            amount_kopecks=state.amount_kopecks,
            currency=state.currency,
            provider_subscription_id=state.provider_subscription_id,
            payload={**event.payload, "verified_state": state.raw},
            signature_valid=True,
        )

    order = None
    if event.provider_payment_id:
        order = await db.scalar(
            select(PaymentOrder)
            .where(PaymentOrder.provider_payment_id == event.provider_payment_id)
            .with_for_update()
        )
    if order is None and event.order_id is not None:
        order = await db.scalar(
            select(PaymentOrder)
            .where(PaymentOrder.id == event.order_id)
            .with_for_update()
        )
    if order is None:
        raise NotFoundError("Заказ для платежа не найден", code="payment_order_not_found")
    if order.provider != provider.name:
        raise ValidationAppError("Провайдер платежа не совпадает", code="provider_mismatch")
    if order.provider_payment_id is None:
        order.provider_payment_id = event.provider_payment_id
    elif (
        event.provider_payment_id is not None
        and order.provider_payment_id != event.provider_payment_id
    ):
        raise ValidationAppError("Платёж не совпадает с заказом", code="payment_mismatch")

    event_id = await _record_event(
        db,
        provider=provider.name,
        event=event,
        order_id=order.id,
        signature_valid=event.signature_valid,
    )
    if event_id is None:
        await db.rollback()
        return "duplicate"

    if event.amount_kopecks is None or event.amount_kopecks != order.amount_kopecks:
        await _mark_event_error(db, event_id, "amount_mismatch")
        await db.commit()
        raise ValidationAppError("Сумма платежа не совпадает", code="amount_mismatch")
    if event.currency is not None and event.currency.upper() != order.currency.upper():
        await _mark_event_error(db, event_id, "currency_mismatch")
        await db.commit()
        raise ValidationAppError("Валюта платежа не совпадает", code="currency_mismatch")

    now = utcnow()
    event_type = event.event_type.lower()
    status = event.status.lower()
    refund_event = event_type.startswith("refund.") or status == "refunded"
    paid_event = status in {"succeeded", "paid", "captured"} or event_type == "payment.succeeded"
    pending_event = status in {"pending", "waiting_for_capture", "created"}
    failed_event = status in {"canceled", "cancelled", "failed"}

    if refund_event:
        if order.status != "refunded":
            order.status = "refunded"
            await _revoke_subscription(
                db,
                order.user_id,
                reason="Платёж возвращён, поэтому платные возможности отключены.",
            )
        result = "refunded"
    elif paid_event:
        if order.status != "paid":
            plan = await db.get(Plan, order.plan_id)
            if plan is None:
                await _mark_event_error(db, event_id, "plan_missing")
                await db.commit()
                raise ValidationAppError("Тариф не найден", code="plan_not_found")
            order.status = "paid"
            order.paid_at = now
            await _activate_subscription(db, order=order, plan=plan, event=event)
            db.add(
                AuditLog(
                    id=uuid4(),
                    actor_id=None,
                    actor_role="system",
                    action="payment.paid",
                    object_type="payment_order",
                    object_id=str(order.id),
                    metadata_json={
                        "provider": order.provider,
                        "amount_kopecks": order.amount_kopecks,
                    },
                )
            )
        result = "paid"
    elif pending_event:
        if order.status in {"created", "pending"}:
            order.status = "pending"
        result = "pending"
    elif failed_event:
        if order.status not in {"paid", "refunded"}:
            order.status = "canceled" if status in {"canceled", "cancelled"} else "failed"
        result = "failed"
    else:
        await _mark_event_error(db, event_id, f"unsupported_status:{status}")
        await db.commit()
        raise ValidationAppError("Неподдерживаемый статус платежа", code="unsupported_status")

    event_row = await db.get(PaymentEvent, event_id)
    if event_row is not None:
        event_row.processed_at = now
    await db.commit()
    return result


async def demo_confirm(
    db: AsyncSession, user: User, order_id: UUID
) -> BillingOrderView:
    if not payments_demo():
        raise NotFoundError("Демо-оплата недоступна", code="demo_payment_unavailable")
    order = await db.scalar(
        select(PaymentOrder).where(
            PaymentOrder.id == order_id, PaymentOrder.user_id == user.id
        )
    )
    if order is None:
        raise NotFoundError("Платёж не найден", code="order_not_found")
    if order.provider != "fake":
        raise ValidationAppError("Заказ не относится к демо-провайдеру", code="not_demo_order")
    if order.status == "paid":
        return await order_view(db, order)
    if order.status not in {"created", "pending"}:
        raise ValidationAppError(
            "Этот платёж уже нельзя подтвердить", code="order_not_payable"
        )
    if order.provider_payment_id is None:
        raise ValidationAppError("Платёж не инициализирован", code="order_invalid")
    provider = get_payment_provider("fake")
    if not isinstance(provider, FakePaymentProvider):
        raise NotFoundError("Демо-оплата недоступна", code="demo_payment_unavailable")
    headers, body = provider.signed_success_webhook(
        order_id=order.id,
        provider_payment_id=order.provider_payment_id,
        amount_kopecks=order.amount_kopecks,
        currency=order.currency,
    )
    await db.commit()
    await process_webhook(db, "fake", headers, body)
    refreshed = await db.get(PaymentOrder, order.id)
    if refreshed is None:
        raise NotFoundError("Платёж не найден", code="order_not_found")
    return await order_view(db, refreshed)


async def admin_payment_detail(
    db: AsyncSession, order_id: UUID
) -> AdminPaymentDetailView:
    order = await db.get(PaymentOrder, order_id)
    if order is None:
        raise NotFoundError("Платёж не найден", code="order_not_found")
    events = (
        await db.scalars(
            select(PaymentEvent)
            .where(PaymentEvent.order_id == order.id)
            .order_by(PaymentEvent.created_at.desc())
            .limit(100)
        )
    ).all()
    return AdminPaymentDetailView(
        order=await order_view(db, order),
        payment_id=order.provider_payment_id,
        events=[
            AdminPaymentEventView(
                provider_event_id=event.provider_event_id,
                event_type=event.event_type,
                status=str((event.payload or {}).get("status") or "unknown"),
                signature_valid=event.signature_valid,
                processed_at=event.processed_at,
                error=event.error,
                created_at=event.created_at,
            )
            for event in events
        ],
    )


async def admin_grant_entitlement(
    db: AsyncSession,
    actor: User,
    user_public_id: UUID,
    *,
    code: str,
    days: int | None,
) -> dict[str, Any]:
    try:
        Entitlement(code)
    except ValueError as exc:
        raise ValidationAppError("Неизвестная возможность", code="unknown_entitlement") from exc
    target = await db.scalar(select(User).where(User.public_id == user_public_id))
    if target is None:
        raise NotFoundError("Пользователь не найден", code="user_not_found")
    expires_at = utcnow() + timedelta(days=days) if days else None
    grant = await db.scalar(
        select(EntitlementGrant).where(
            EntitlementGrant.user_id == target.id,
            EntitlementGrant.code == code,
            EntitlementGrant.source == "manual",
        )
    )
    if grant is None:
        grant = EntitlementGrant(
            id=uuid4(),
            user_id=target.id,
            code=code,
            source="manual",
            granted_by=actor.id,
            expires_at=expires_at,
        )
        db.add(grant)
    else:
        grant.granted_by = actor.id
        grant.expires_at = expires_at
    db.add(
        AuditLog(
            id=uuid4(),
            actor_id=actor.id,
            actor_role=actor.role,
            action="entitlement.grant",
            object_type="user",
            object_id=str(target.public_id),
            metadata_json={"code": code, "days": days},
        )
    )
    await db.commit()
    await db.refresh(grant)
    return {
        "code": grant.code,
        "source": grant.source,
        "expires_at": grant.expires_at,
        "created_at": grant.created_at,
    }


async def admin_revoke_entitlement(
    db: AsyncSession, actor: User, user_public_id: UUID, code: str
) -> None:
    target = await db.scalar(select(User).where(User.public_id == user_public_id))
    if target is None:
        raise NotFoundError("Пользователь не найден", code="user_not_found")
    result = await db.execute(
        delete(EntitlementGrant).where(
            EntitlementGrant.user_id == target.id,
            EntitlementGrant.code == code,
            EntitlementGrant.source == "manual",
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise NotFoundError("Выдача не найдена", code="entitlement_not_found")
    db.add(
        AuditLog(
            id=uuid4(),
            actor_id=actor.id,
            actor_role=actor.role,
            action="entitlement.revoke",
            object_type="user",
            object_id=str(target.public_id),
            metadata_json={"code": code},
        )
    )
    await db.commit()


async def admin_refund(
    db: AsyncSession,
    actor: User,
    order_id: UUID,
    *,
    reason: str,
) -> PaymentOrder:
    order = await db.scalar(
        select(PaymentOrder).where(PaymentOrder.id == order_id).with_for_update()
    )
    if order is None:
        raise NotFoundError("Платёж не найден", code="order_not_found")
    if order.status != "paid":
        raise ValidationAppError(
            "Возврат возможен только для оплаченного платежа", code="order_not_refundable"
        )
    if order.provider_payment_id is None:
        raise ValidationAppError("У платежа нет идентификатора провайдера", code="order_invalid")
    provider = get_payment_provider(order.provider)
    provider_refund_id = await provider.refund(
        order.provider_payment_id,
        order.amount_kopecks,
        f"refund:{order.id}",
    )
    db.add(
        Refund(
            id=uuid4(),
            order_id=order.id,
            amount_kopecks=order.amount_kopecks,
            reason=reason.strip()[:400],
            provider_refund_id=provider_refund_id,
            status="succeeded",
        )
    )
    order.status = "refunded"
    await _revoke_subscription(
        db,
        order.user_id,
        reason="Платёж возвращён. Платные возможности отключены.",
    )
    db.add(
        AuditLog(
            id=uuid4(),
            actor_id=actor.id,
            actor_role=actor.role,
            action="payment.refund",
            object_type="payment_order",
            object_id=str(order.id),
            metadata_json={"reason": reason[:400]},
        )
    )
    await db.commit()
    await db.refresh(order)
    return order


async def reconcile(db: AsyncSession) -> dict[str, int]:
    now = utcnow()
    paid_users = select(PaymentOrder.user_id).where(PaymentOrder.status == "paid").distinct()
    active_users = select(Subscription.user_id).where(
        Subscription.status.in_(["active", "past_due"]),
        Subscription.current_period_end.is_not(None),
        Subscription.current_period_end > now,
    )
    paid_count = int(
        await db.scalar(
            select(func.count()).select_from(PaymentOrder).where(PaymentOrder.status == "paid")
        )
        or 0
    )
    active_count = int(
        await db.scalar(
            select(func.count()).select_from(Subscription).where(
                Subscription.status.in_(["active", "past_due"]),
                Subscription.current_period_end.is_not(None),
                Subscription.current_period_end > now,
            )
        )
        or 0
    )
    paid_without_subscription = int(
        await db.scalar(
            select(func.count()).select_from(paid_users.except_(active_users).subquery())
        )
        or 0
    )
    subscription_without_payment = int(
        await db.scalar(
            select(func.count()).select_from(active_users.except_(paid_users).subquery())
        )
        or 0
    )
    refunded_total = int(
        await db.scalar(
            select(func.coalesce(func.sum(Refund.amount_kopecks), 0)).where(
                Refund.status == "succeeded"
            )
        )
        or 0
    )
    return {
        "paid_orders": paid_count,
        "active_subscriptions": active_count,
        "paid_without_subscription": paid_without_subscription,
        "subscription_without_payment": subscription_without_payment,
        "refunded_kopecks": refunded_total,
    }
