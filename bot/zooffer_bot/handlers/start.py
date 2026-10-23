from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import AppError
from zooffer.core.utils import validate_display_name
from zooffer.db.models import User
from zooffer.services import auth_service

from .. import services, texts
from ..config import BotConfig
from ..keyboards import consent_keyboard, link_confirm_keyboard, name_keyboard
from ..states import LinkFlow, Onboarding
from .common import (
    persistent_keyboard,
    safe_callback_answer,
    send_listing_detail,
    send_main_menu,
    send_main_menu_to_bot,
)

router = Router(name="start")


async def _apply_payload(
    bot: Bot,
    chat_id: int,
    db: AsyncSession,
    user: User,
    payload: str,
) -> None:
    if not payload or payload.startswith("link_"):
        return
    if payload.startswith("ref_"):
        await services.record_referral(db, user, payload[4:])
        return
    if payload.startswith("utm_"):
        await services.record_campaign(db, user, payload[4:].split("_", 2))
        return
    if payload.startswith("listing_"):
        public_id = await services.parse_listing_public_id(payload[8:])
        if public_id is None:
            return
        try:
            listing = await services.get_public_listing(db, str(public_id))
        except AppError:
            await bot.send_message(
                chat_id=chat_id, text="Объявление не найдено или уже снято с публикации."
            )
            return
        await send_listing_detail(bot, chat_id, listing)


async def _complete_onboarding(
    bot: Bot,
    chat_id: int,
    message: Message | None,
    state: FSMContext,
    db: AsyncSession,
    user: User,
    config: BotConfig,
) -> None:
    data = await state.get_data()
    payload = str(data.get("deep_link") or "")
    await state.clear()
    await services.link_telegram_chat(db, user, chat_id=chat_id)
    name = await services.public_name_for(db, user)
    target = message or bot
    if isinstance(target, Message):
        await target.answer(
            texts.welcome_text(name), reply_markup=persistent_keyboard(config)
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=texts.welcome_text(name),
            reply_markup=persistent_keyboard(config),
        )
    await _apply_payload(bot, chat_id, db, user, payload)
    await send_main_menu_to_bot(bot, chat_id, user, db, config)


async def _start_or_resume(
    message: Message,
    *,
    user: User | None,
    tg_user,
    state: FSMContext,
    db: AsyncSession,
    bot: Bot,
    config: BotConfig,
) -> None:
    if user is not None:
        await state.clear()
        await services.link_telegram_chat(db, user, chat_id=message.chat.id)
        name = await services.public_name_for(db, user)
        await message.answer(
            texts.welcome_text(name), reply_markup=persistent_keyboard(config)
        )
        await send_main_menu(message, user, db, config)
        return
    suggested = None
    if tg_user is not None:
        try:
            suggested = validate_display_name(tg_user.first_name)
        except ValueError:
            suggested = None
    await state.set_state(Onboarding.consent)
    await state.update_data(suggested_name=suggested)
    await message.answer(texts.consent_text(), reply_markup=consent_keyboard())


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    tg_user,
    bot: Bot,
    config: BotConfig,
) -> None:
    payload = (command.args or "").strip()
    if payload.startswith("link_"):
        await state.clear()
        if user is not None:
            await message.answer(
                "Этот Telegram уже привязан к аккаунту Zooffer.",
                reply_markup=persistent_keyboard(config),
            )
            await send_main_menu(message, user, db, config)
            return
        if tg_user is None:
            await message.answer(texts.generic_error_text())
            return
        await state.set_state(LinkFlow.confirm)
        await state.update_data(link_token=payload[5:])
        await message.answer(
            texts.link_confirm_text(),
            reply_markup=link_confirm_keyboard(),
        )
        return

    if user is None and payload:
        await _start_or_resume(
            message,
            user=None,
            tg_user=tg_user,
            state=state,
            db=db,
            bot=bot,
            config=config,
        )
        await state.update_data(deep_link=payload)
        return

    await _start_or_resume(
        message,
        user=user,
        tg_user=tg_user,
        state=state,
        db=db,
        bot=bot,
        config=config,
    )
    if user is not None and payload:
        await _apply_payload(bot, message.chat.id, db, user, payload)


@router.callback_query(F.data, StateFilter(LinkFlow.confirm))
async def link_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    tg_user,
    bot: Bot,
    config: BotConfig,
) -> None:
    from ..callbacks import unpack

    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "link":
        await safe_callback_answer(callback, "Кнопка устарела. Откройте новую ссылку.")
        return
    if parts[1] == "cancel":
        await state.clear()
        await safe_callback_answer(callback, "Привязка отменена")
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "Привязка отменена. Ссылку можно создать заново в настройках сайта."
            )
        return
    if parts[1] != "confirm":
        await safe_callback_answer(callback)
        return
    data = await state.get_data()
    raw_token = data.get("link_token")
    if tg_user is None or not isinstance(raw_token, str) or not raw_token:
        await state.clear()
        await safe_callback_answer(
            callback, "Ссылка устарела. Создайте новую в настройках сайта.", show_alert=True
        )
        return
    try:
        linked = await auth_service.confirm_link_token(
            db, raw_token=raw_token, telegram_id=str(tg_user.id)
        )
    except AppError as exc:
        await state.clear()
        await safe_callback_answer(callback, exc.message, show_alert=True)
        if callback.message is not None:
            await callback.message.answer(
                f"{exc.message}\n\nОткройте новую ссылку в настройках сайта."
            )
        return
    await state.clear()
    chat_id = callback.message.chat.id if callback.message is not None else tg_user.id
    await services.link_telegram_chat(db, linked, chat_id=chat_id)
    await safe_callback_answer(callback, "Telegram привязан")
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        name = await services.public_name_for(db, linked)
        await callback.message.answer(
            texts.welcome_text(name), reply_markup=persistent_keyboard(config)
        )
        await send_main_menu(callback.message, linked, db, config)


@router.callback_query(F.data, StateFilter(Onboarding.consent))
async def onboarding_consent(callback: CallbackQuery, state: FSMContext) -> None:
    from ..callbacks import unpack

    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "onb":
        await safe_callback_answer(callback, "Кнопка устарела. Откройте /start.")
        return
    action = parts[1]
    if action == "cancel":
        await state.clear()
        await safe_callback_answer(callback, "Регистрация отменена")
        if callback.message:
            await callback.message.answer(
                "Регистрация отменена. Чтобы начать снова, отправьте /start."
            )
        return
    if action != "accept":
        await safe_callback_answer(callback)
        return
    data = await state.get_data()
    suggested = data.get("suggested_name")
    await state.set_state(Onboarding.name)
    await safe_callback_answer(callback)
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            texts.name_prompt_text(suggested if isinstance(suggested, str) else None),
            reply_markup=name_keyboard(suggested if isinstance(suggested, str) else None),
        )


async def _create_account_from_name(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    tg_user,
    bot: Bot,
    config: BotConfig,
    name: str,
) -> None:
    try:
        cleaned = validate_display_name(name)
    except ValueError:
        await message.answer(texts.invalid_name_text())
        return
    try:
        user = await auth_service.create_telegram_bot_user(
            db,
            telegram_id=str(tg_user.id),
            public_first_name=cleaned,
            accepted_terms=True,
            accepted_privacy=True,
            channel="telegram",
        )
    except AppError as exc:
        await message.answer(exc.message)
        return
    await _complete_onboarding(
        bot, message.chat.id, message, state, db, user, config
    )


@router.callback_query(F.data, StateFilter(Onboarding.name))
async def onboarding_use_suggested(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    tg_user,
    bot: Bot,
    config: BotConfig,
) -> None:
    from ..callbacks import unpack

    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "onb":
        await safe_callback_answer(callback, "Кнопка устарела. Откройте /start.")
        return
    if parts[1] == "cancel":
        await state.clear()
        await safe_callback_answer(callback, "Регистрация отменена")
        if callback.message:
            await callback.message.answer(
                "Регистрация отменена. Чтобы начать снова, отправьте /start."
            )
        return
    if parts[1] != "suggested":
        await safe_callback_answer(callback)
        return
    data = await state.get_data()
    suggested = data.get("suggested_name")
    if not isinstance(suggested, str) or not suggested:
        await safe_callback_answer(
            callback, "Напишите имя сообщением.", show_alert=True
        )
        return
    await safe_callback_answer(callback)
    if callback.message is None:
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await _create_account_from_name(
        callback.message, state, db, tg_user, bot, config, suggested
    )


@router.message(StateFilter(Onboarding.name), F.text)
async def onboarding_name(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    tg_user,
    bot: Bot,
    config: BotConfig,
) -> None:
    if tg_user is None:
        await message.answer(texts.generic_error_text())
        return
    await _create_account_from_name(
        message, state, db, tg_user, bot, config, message.text or ""
    )
