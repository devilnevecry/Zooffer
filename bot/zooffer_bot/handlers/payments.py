from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import AppError
from zooffer.db.models import User

from .. import services

router = Router(name="payments")


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, db: AsyncSession) -> None:
    """Validate a Stars invoice before Telegram charges the user."""
    if query.currency != "XTR":
        await query.answer(ok=False, error_message="Оплата возможна только в Telegram Stars.")
        return
    try:
        await services.validate_stars_precheckout(
            db, payload=query.invoice_payload, total_amount=query.total_amount
        )
    except AppError as exc:
        await query.answer(ok=False, error_message=exc.message)
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message,
    db: AsyncSession,
    user: User | None,
    tg_user,
) -> None:
    payment = message.successful_payment
    if payment is None:
        return
    if user is None or tg_user is None:
        await message.answer(
            "Платёж получен, но аккаунт не найден. "
            "Напишите в /support — мы активируем подписку вручную."
        )
        return
    try:
        order = await services.confirm_stars_payment(
            db,
            payload=payment.invoice_payload,
            charge_id=payment.telegram_payment_charge_id,
            telegram_user_id=tg_user.id,
            total_amount=payment.total_amount,
            currency=payment.currency,
        )
    except AppError as exc:
        await message.answer(
            f"Не удалось активировать подписку автоматически: {exc.message}\n\n"
            "Напишите в /support, приложив номер платежа."
        )
        return
    await message.answer(
        "<b>Оплата получена</b>\n\n"
        f"Подписка активирована. Номер заказа: <code>{order.id}</code>.\n"
        "Продление ручное: автоматических списаний нет. Управление — в /subscription."
    )
