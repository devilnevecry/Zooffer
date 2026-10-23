from __future__ import annotations

import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import AppError
from zooffer.db.models import User

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import favorites_keyboard
from .common import ensure_onboarded, safe_callback_answer

router = Router(name="favorites")


async def show_favorites(
    message: Message,
    db: AsyncSession,
    user: User,
) -> None:
    items = await services.favorites(db, user)
    labels = [
        (str(listing.public_id), animal.name or listing.title) for listing, animal in items
    ]
    await message.answer(
        texts.favorites_text(len(items)),
        reply_markup=favorites_keyboard(labels),
    )


@router.message(Command("favorites"))
async def cmd_favorites(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        if await ensure_onboarded(message, user, state, config):
            return
        return
    await state.clear()
    await show_favorites(message, db, user)


@router.callback_query(F.data.startswith(prefix("fav:")))
async def favorite_callback(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    parts = unpack(callback.data, 3)
    if parts is None or parts[0] != "fav":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if parts[1] != "rm":
        await safe_callback_answer(callback)
        return
    listing_public_id = await services.parse_listing_public_id(parts[2])
    if listing_public_id is None:
        await safe_callback_answer(callback, "Объявление не найдено.")
        return
    try:
        await services.remove_favorite(db, user, listing_public_id)
    except AppError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    await safe_callback_answer(callback, "Удалено из избранного")
    if callback.message is not None:
        with contextlib.suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
        await show_favorites(callback.message, db, user)
