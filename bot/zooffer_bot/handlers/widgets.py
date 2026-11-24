"""Telegram widget screens and widget queries (Bot API 10.4)."""

from __future__ import annotations

import contextlib
import json
import os
from time import time
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, WidgetQuery
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.config import settings
from zooffer.db.models import PaymentOrder
from zooffer.services import auth_service

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import back_menu_keyboard
from ..widgets import crypto_widget_html, subscription_widget_html
from .common import ensure_onboarded, safe_callback_answer

router = Router(name="widgets")

TON_AMOUNT = float(os.getenv("CRYPTO_PAYMENT_TON_AMOUNT", "0.05"))


def _subscription_data(view) -> str:  # type: ignore[no-untyped-def]
    return json.dumps(
        {
            "plan": view.plan_name or "Бесплатный",
            "until": view.current_period_end.strftime("%d.%m.%Y")
            if view.current_period_end
            else "—",
            "quota": "без лимита" if view.quota_unlimited else f"{view.quota_limit} в день",
            "features": list(view.entitlements)[:6],
            "status": (
                "Активна" if view.status in {"active", "past_due"} else "Нет активной подписки"
            ),
        }
    )


async def send_subscription_widget(
    bot: Bot,
    chat_id: int,
    user,
    db: AsyncSession,
    config: BotConfig,  # type: ignore[no-untyped-def]
) -> None:
    view = await services.get_subscription_view(db, user)
    await bot.send_widget(
        chat_id=chat_id,
        html=subscription_widget_html(f"https://t.me/{config.bot_username}"),
        caption=texts.subscription_text(view),
        chat_data=_subscription_data(view),
        allow_queries=True,
        reply_markup=back_menu_keyboard("subscription"),
    )


@router.message(Command("widget"))
async def cmd_widget(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user,  # type: ignore[no-untyped-def]
    config: BotConfig,
    bot: Bot,
) -> None:
    if user is None:
        await ensure_onboarded(message, user, state, config)
        return
    try:
        await send_subscription_widget(bot, message.chat.id, user, db, config)
    except TelegramBadRequest:
        await message.answer("Виджеты пока недоступны в вашем Telegram. Пользуйтесь /menu.")


@router.callback_query(F.data.startswith(prefix("widget:")))
async def widget_status_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    user,  # type: ignore[no-untyped-def]
    config: BotConfig,
    bot: Bot,
) -> None:
    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "widget":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if user is None or callback.message is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await safe_callback_answer(callback)
    try:
        await send_subscription_widget(bot, callback.message.chat.id, user, db, config)
    except TelegramBadRequest:
        await safe_callback_answer(
            callback, "Виджеты пока недоступны в вашем Telegram. Пользуйтесь меню.", show_alert=True
        )


@router.callback_query(F.data.startswith(prefix("widgetpay:")))
async def widget_payment_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    bot: Bot,
    user,  # type: ignore[no-untyped-def]
) -> None:
    parts = unpack(callback.data, 4)
    if parts is None or parts[0] != "widgetpay":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if user is None or callback.message is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    try:
        order, plan = await services.prepare_crypto_order(db, user, parts[2], months=int(parts[3]))
    except Exception:  # provider errors are surfaced as a short alert
        await safe_callback_answer(callback, "Не удалось создать платёж", show_alert=True)
        return
    await safe_callback_answer(callback)
    try:
        await _send_payment_widget(callback.message.chat.id, order, plan, bot)
    except TelegramBadRequest:
        await safe_callback_answer(
            callback,
            "Виджеты пока недоступны. Используйте обычную оплату криптой.",
            show_alert=True,
        )


async def _send_payment_widget(
    chat_id: int,
    order: PaymentOrder,
    plan,
    bot: Bot,  # type: ignore[no-untyped-def]
) -> None:
    await bot.send_widget(
        chat_id=chat_id,
        html=crypto_widget_html(),
        caption=(
            f"💎 Оплата: {plan.name} · {order.amount_kopecks / 100:.2f} {order.currency}\n"
            f"Код платежа: {order.id}"
        ),
        chat_data=json.dumps(
            {
                "summary": f"{plan.name} · {order.amount_kopecks / 100:.2f} {order.currency}",
                "wallet": settings.crypto_payment_wallet_address,
                "order": str(order.id),
                "amount": f"{TON_AMOUNT:g}",
            }
        ),
        allow_queries=True,
        reply_markup=back_menu_keyboard("subscription"),
    )


@router.widget_query()
async def answer_widget_query(query: WidgetQuery, bot: Bot, db: AsyncSession) -> None:
    data = query.data or ""
    if data == "refresh":
        user = await auth_service.find_telegram_user(db, str(query.from_user.id))
        if user is None:
            await bot.answer_widget_query(query.id, data="{}")
            return
        view = await services.get_subscription_view(db, user)
        if query.chat is not None and query.message_id is not None:
            with contextlib.suppress(TelegramBadRequest):
                await bot.edit_message_widget_data(
                    chat_id=query.chat.id,
                    message_id=query.message_id,
                    chat_data=_subscription_data(view),
                )
        await bot.answer_widget_query(query.id, data=json.dumps({"ok": True}))
        return
    if data.startswith("pay:"):
        order_id = _parse_order(data[4:])
        user = await auth_service.find_telegram_user(db, str(query.from_user.id))
        order = await db.get(PaymentOrder, order_id) if order_id is not None else None
        if user is None or order is None or order.user_id != user.id or order.status != "pending":
            await bot.answer_widget_query(query.id, data=json.dumps({"error": "order_unavailable"}))
            return
        transaction = {
            "valid_until": int(time()) + 600,
            "messages": [
                {
                    "address": settings.crypto_payment_wallet_address,
                    "amount": str(int(TON_AMOUNT * 1_000_000_000)),
                }
            ],
        }
        await bot.answer_widget_query(query.id, data=json.dumps(transaction))
        return
    if data.startswith("paid:"):
        order_id = _parse_order(data[5:])
        order = await db.get(PaymentOrder, order_id) if order_id is not None else None
        if order is not None:
            msg_hash = getattr(query.type, "msg_hash", None)
            wallet = getattr(query.type, "wallet", None)
            order.raw_metadata = {
                **(order.raw_metadata or {}),
                "widget_tx_hash": msg_hash,
                "widget_wallet_address": getattr(wallet, "address", None),
            }
            await db.commit()
        await bot.answer_widget_query(query.id, data=json.dumps({"ok": True}))
        return
    await bot.answer_widget_query(query.id, data="{}")


def _parse_order(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
