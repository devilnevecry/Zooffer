from __future__ import annotations

import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    QuotaExceededError,
)
from zooffer.db.models import User

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import (
    match_keyboard,
    next_keyboard,
    subscription_keyboard,
    swipe_keyboard,
)
from .common import ensure_onboarded, safe_callback_answer, send_listing_card

router = Router(name="discovery")


async def show_next_listing(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    config: BotConfig,
) -> None:
    await state.clear()
    items, remaining, unlimited = await services.next_feed_item(db, user)
    if not items:
        await message.answer(texts.no_new_listings_text(), reply_markup=next_keyboard())
        return
    item = items[0]
    await send_listing_card(
        message.bot,
        message.chat.id,
        item,
        remaining=remaining,
        unlimited=unlimited,
        reply_markup=swipe_keyboard(str(item.public_id)),
    )


@router.message(Command("swipe"))
async def cmd_swipe(
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
    await show_next_listing(message, state, db, user, config)


@router.callback_query(F.data.startswith(prefix("sw:")))
async def swipe_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    parts = unpack(callback.data, 3)
    if parts is None or parts[0] != "sw":
        await safe_callback_answer(callback, "Кнопка устарела. Откройте /swipe.")
        return
    action, raw_id = parts[1], parts[2]
    if callback.message is None:
        await safe_callback_answer(callback)
        return
    listing_public_id = await services.parse_listing_public_id(raw_id)
    if listing_public_id is None:
        await safe_callback_answer(callback, "Объявление не найдено.")
        return
    if action == "fav":
        try:
            await services.add_favorite(db, user, listing_public_id)
        except (NotFoundError, ForbiddenError) as exc:
            await safe_callback_answer(callback, exc.message, show_alert=True)
            return
        await safe_callback_answer(callback, "Добавлено в избранное")
        return
    if action not in {"like", "skip"}:
        await safe_callback_answer(callback)
        return

    from zooffer.core.enums import SwipeAction

    try:
        result = await services.perform_swipe(
            db,
            user,
            listing_public_id,
            SwipeAction.LIKE if action == "like" else SwipeAction.SKIP,
        )
    except QuotaExceededError as exc:
        reset_at = None
        if isinstance(exc.details, dict):
            reset_at = exc.details.get("resets_at")
        await safe_callback_answer(callback, exc.message, show_alert=True)
        await callback.message.answer(
            texts.quota_exceeded_text(str(reset_at) if reset_at else None),
            reply_markup=subscription_keyboard(True),
        )
        return
    except ConflictError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    except (NotFoundError, ForbiddenError) as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    except AppError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return

    with contextlib.suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    await state.clear()
    if result.match_created and result.conversation_public_id is not None:
        await safe_callback_answer(callback, "Взаимная симпатия")
        await callback.message.answer(
            texts.match_text(),
            reply_markup=match_keyboard(str(result.conversation_public_id)),
        )
        return
    await safe_callback_answer(callback, "Лайк отправлен" if action == "like" else "Пропущено")
    await show_next_listing(callback.message, state, db, user, config)
