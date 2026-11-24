from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from zooffer.api.deps import CurrentAuth, DbSession, client_ip
from zooffer.core.errors import ValidationAppError
from zooffer.core.rate_limit import limiter
from zooffer.schemas.billing import (
    BillingOrderCreateRequest,
    BillingOrderList,
    BillingOrderView,
    StarsInvoiceView,
)
from zooffer.services import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])

MAX_WEBHOOK_BYTES = 256 * 1024


@router.get("/orders", response_model=BillingOrderList)
async def list_orders(auth: CurrentAuth, db: DbSession) -> BillingOrderList:
    return BillingOrderList(items=await billing_service.list_orders(db, auth.user))


@router.post("/orders", response_model=BillingOrderView, status_code=201)
async def create_order(
    payload: BillingOrderCreateRequest, auth: CurrentAuth, db: DbSession
) -> BillingOrderView:
    await limiter.hit(f"billing-order:{auth.user.id}", limit=10, window_seconds=3600)
    return await billing_service.create_order(db, auth.user, payload.plan_code)


@router.post("/stars/invoice", response_model=StarsInvoiceView, status_code=201)
async def create_stars_invoice(
    payload: BillingOrderCreateRequest, auth: CurrentAuth, db: DbSession
) -> StarsInvoiceView:
    """Create a Telegram Stars invoice link for the Mini App.

    The website never calls this endpoint: Stars invoices only open inside
    Telegram. The bot sends the same order through ``sendInvoice``.
    """
    await limiter.hit(f"stars-invoice:{auth.user.id}", limit=20, window_seconds=3600)
    return await billing_service.create_stars_invoice(db, auth.user, payload.plan_code)


@router.post("/crypto/orders", response_model=BillingOrderView, status_code=201)
async def create_crypto_order(
    payload: BillingOrderCreateRequest, auth: CurrentAuth, db: DbSession
) -> BillingOrderView:
    """Create a crypto wallet payment order (additional path next to Telegram Stars)."""
    await limiter.hit(f"crypto-order:{auth.user.id}", limit=10, window_seconds=3600)
    order, _plan = await billing_service.prepare_crypto_order(db, auth.user, payload.plan_code)
    return await billing_service.order_view(db, order)


@router.get("/orders/{order_id}", response_model=BillingOrderView)
async def get_order(order_id: UUID, auth: CurrentAuth, db: DbSession) -> BillingOrderView:
    return await billing_service.get_order(db, auth.user, order_id)


@router.post("/orders/{order_id}/demo-confirm", response_model=BillingOrderView)
async def demo_confirm(order_id: UUID, auth: CurrentAuth, db: DbSession) -> BillingOrderView:
    await limiter.hit(f"billing-demo:{auth.user.id}", limit=20, window_seconds=3600)
    return await billing_service.demo_confirm(db, auth.user, order_id)


@router.post("/webhooks/{provider_name}", include_in_schema=False)
async def payment_webhook(provider_name: str, request: Request, db: DbSession) -> object:
    """Provider callback endpoint. Authenticity is checked per provider."""
    ip = client_ip(request) or "unknown"
    await limiter.hit(f"payment-webhook:{ip}", limit=600, window_seconds=60)
    body = await request.body()
    if not body:
        raise ValidationAppError("Пустое уведомление платёжной системы", code="empty_webhook")
    if len(body) > MAX_WEBHOOK_BYTES:
        raise ValidationAppError(
            "Уведомление платёжной системы слишком большое", code="webhook_too_large"
        )
    result = await billing_service.process_webhook(db, provider_name, dict(request.headers), body)
    if provider_name.lower() == "robokassa":
        # Robokassa expects the literal body ``OK<InvId>`` to mark the ResultURL
        # as delivered. InvId is the provider payment id stored on the order.
        inv_id = ""
        try:
            from urllib.parse import parse_qsl

            fields = dict(parse_qsl(body.decode("utf-8")))
            inv_id = fields.get("InvId", "")
        except (UnicodeDecodeError, ValueError):
            inv_id = ""
        return PlainTextResponse(f"OK{inv_id}")
    return {"ok": True, "result": result}
