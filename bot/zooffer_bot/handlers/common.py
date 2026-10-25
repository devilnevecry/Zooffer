from __future__ import annotations

import contextlib
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.db.models import User
from zooffer.schemas.public import PublicListingCardView

from .. import texts
from ..config import BotConfig
from ..keyboards import consent_keyboard, main_menu, main_reply_keyboard
from ..services import public_name_for
from ..states import Onboarding


def photo_url_usable(url: str | None) -> bool:
    if not url or not url.startswith(("http://", "https://")):
        return False
    lowered = url.lower()
    # Reject URLs pointing at loopback or wildcard hosts.
    return not any(
        host in lowered
        for host in ("localhost", "127.0.0.1", "0.0.0.0")  # noqa: S104  # nosec B104
    )


async def send_listing_card(
    bot: Bot,
    chat_id: int,
    item: PublicListingCardView,
    *,
    remaining: int,
    unlimited: bool,
    reply_markup: InlineKeyboardMarkup,
) -> Message:
    caption = texts.listing_card_text(item, remaining, unlimited)
    url = item.primary_photo.url if item.primary_photo else None
    if photo_url_usable(url):
        try:
            return await bot.send_photo(
                chat_id=chat_id,
                photo=url,
                caption=caption,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest:
            pass
    return await bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup)


async def send_listing_detail(bot: Bot, chat_id: int, listing) -> None:
    from ..keyboards import public_listing_keyboard

    text = texts.listing_detail_text(listing)
    markup = public_listing_keyboard(str(listing.public_id))
    photos = listing.animal.photos
    url = photos[0].url if photos else None
    if photo_url_usable(url) and len(text) <= 1024:
        try:
            await bot.send_photo(chat_id=chat_id, photo=url, caption=text, reply_markup=markup)
            return
        except TelegramBadRequest:
            pass
    if photo_url_usable(url):
        with contextlib.suppress(TelegramBadRequest):
            await bot.send_photo(chat_id=chat_id, photo=url, caption=escape(listing.title))
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)


async def send_main_menu(
    message: Message,
    user: User,
    db: AsyncSession,
    config: BotConfig,
) -> None:
    name = await public_name_for(db, user)
    await message.answer(
        texts.menu_text(name),
        reply_markup=main_menu(config.mini_app_url),
    )


async def send_main_menu_to_bot(
    bot: Bot,
    chat_id: int,
    user: User,
    db: AsyncSession,
    config: BotConfig,
) -> None:
    name = await public_name_for(db, user)
    await bot.send_message(
        chat_id=chat_id,
        text=texts.menu_text(name),
        reply_markup=main_menu(config.mini_app_url),
    )


async def ensure_onboarded(message: Message, user: User | None, state, config: BotConfig) -> bool:
    """Send consent prompt when the chat has no account yet. Returns whether ready."""
    if user is not None:
        return True
    await state.set_state(Onboarding.consent)
    await message.answer(
        texts.consent_text(),
        reply_markup=consent_keyboard(),
    )
    return False


async def safe_callback_answer(
    callback: CallbackQuery, text: str | None = None, *, show_alert: bool = False
) -> None:
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest:
        return


def persistent_keyboard(config: BotConfig):
    return main_reply_keyboard(config.mini_app_url)
