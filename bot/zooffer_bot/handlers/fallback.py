from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from .common import safe_callback_answer

router = Router(name="fallback")


@router.callback_query(F.data)
async def stale_callback(callback: CallbackQuery) -> None:
    """Always answer unhandled callbacks so Telegram stops the button spinner."""
    await safe_callback_answer(callback, "Кнопка устарела. Откройте /menu и попробуйте снова.")


@router.message(F.text)
async def unexpected_text(message: Message) -> None:
    await message.answer("Не понял команду. Откройте /menu или воспользуйтесь кнопками ниже.")
