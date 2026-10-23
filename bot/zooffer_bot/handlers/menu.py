from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.db.models import User

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import (
    main_menu,
    news_keyboard,
    plans_keyboard,
    settings_keyboard,
    subscription_keyboard,
)
from .common import ensure_onboarded, safe_callback_answer, send_main_menu

router = Router(name="menu")


async def _guard(
    message: Message,
    user: User | None,
    state: FSMContext,
    config: BotConfig,
) -> bool:
    if user is not None:
        return True
    return bool(await ensure_onboarded(message, user, state, config))


@router.message(Command("menu"))
async def cmd_menu(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    await state.clear()
    await send_main_menu(message, user, db, config)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.help_text())


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    await state.clear()
    await message.answer("Действие отменено.")
    if user is not None:
        await send_main_menu(message, user, db, config)


@router.message(Command("profile"))
async def cmd_profile(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    from ..keyboards import profile_keyboard

    name = await services.public_name_for(db, user)
    city = await services.city_name_for(db, user)
    await message.answer(
        texts.profile_text(name, city, user.role),
        reply_markup=profile_keyboard(config.mini_app_url),
    )


@router.message(Command("settings"))
async def cmd_settings(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    enabled = await services.telegram_notifications_enabled(db, user.id)
    await message.answer(
        texts.settings_text(enabled),
        reply_markup=settings_keyboard(enabled),
    )


@router.message(Command("stop"))
async def cmd_stop(
    message: Message,
    db: AsyncSession,
    user: User | None,
    state: FSMContext,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    await services.set_all_telegram_preferences(db, user.id, False)
    await message.answer(texts.settings_disabled_note())


@router.message(Command("news"))
async def cmd_news(message: Message, config: BotConfig) -> None:
    await message.answer(
        texts.news_text(config.channel_url),
        reply_markup=news_keyboard(config.channel_url),
    )


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    await message.answer(texts.language_text())


@router.message(Command("link"))
async def cmd_link(
    message: Message,
    db: AsyncSession,
    user: User | None,
    state: FSMContext,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    await message.answer(texts.link_text(config.bot_username))


@router.message(Command("subscription"))
async def cmd_subscription(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    view = await services.get_subscription_view(db, user)
    plans = await services.plan_views(db)
    await message.answer(
        texts.subscription_text(view),
        reply_markup=subscription_keyboard(bool(plans)),
    )


@router.message(Command("buy"))
async def cmd_buy(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    plans = await services.plan_views(db)
    available = services.payments_available()
    await message.answer(
        texts.plans_text(bool(plans), available),
        reply_markup=plans_keyboard(
            [
                (
                    plan.code,
                    f"{plan.name} · {plan.price_kopecks / 100:,.0f} ₽ / "
                    f"{plan.period_days} дн.".replace(",", " "),
                )
                for plan in plans
            ]
        )
        if plans and available
        else main_menu(config.mini_app_url),
    )
    if plans and not available:
        await message.answer(texts.plan_payment_unavailable_text())


@router.message(Command("paysupport"))
async def cmd_paysupport(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    await message.answer(
        "<b>Поддержка по оплате</b>\n\n"
        "Опишите проблему со списанием, возвратом или доступом. "
        "Не присылайте полные данные карты и коды подтверждения.\n\n"
        "Откройте /support, чтобы создать обращение.",
    )


@router.callback_query(F.data.startswith(prefix("menu:")))
async def menu_callbacks(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "menu":
        await safe_callback_answer(callback, "Кнопка устарела. Откройте /menu.")
        return
    action = parts[1]
    if callback.message is None:
        await safe_callback_answer(callback)
        return
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        await ensure_onboarded(callback.message, user, state, config)
        return

    if action == "home":
        await state.clear()
        await safe_callback_answer(callback, "Меню")
        await send_main_menu(callback.message, user, db, config)
        return
    if action == "help":
        await safe_callback_answer(callback)
        await callback.message.answer(texts.help_text())
        return
    if action == "profile":
        await safe_callback_answer(callback)
        from ..keyboards import profile_keyboard

        name = await services.public_name_for(db, user)
        city = await services.city_name_for(db, user)
        await callback.message.answer(
            texts.profile_text(name, city, user.role),
            reply_markup=profile_keyboard(config.mini_app_url),
        )
        return
    if action == "settings":
        await safe_callback_answer(callback)
        enabled = await services.telegram_notifications_enabled(db, user.id)
        await callback.message.answer(
            texts.settings_text(enabled), reply_markup=settings_keyboard(enabled)
        )
        return
    if action == "subscription":
        await safe_callback_answer(callback)
        view = await services.get_subscription_view(db, user)
        plans = await services.plan_views(db)
        await callback.message.answer(
            texts.subscription_text(view),
            reply_markup=subscription_keyboard(bool(plans)),
        )
        return
    if action == "buy":
        await safe_callback_answer(callback)
        plans = await services.plan_views(db)
        available = services.payments_available()
        await callback.message.answer(
            texts.plans_text(bool(plans), available),
            reply_markup=plans_keyboard(
                [(plan.code, plan.name) for plan in plans]
            )
            if plans and available
            else main_menu(config.mini_app_url),
        )
        if plans and not available:
            await callback.message.answer(texts.plan_payment_unavailable_text())
        return
    if action == "support":
        await safe_callback_answer(callback)
        from .support import begin_support

        await begin_support(callback.message, state)
        return
    if action == "swipe":
        await safe_callback_answer(callback)
        from .discovery import show_next_listing

        await show_next_listing(callback.message, state, db, user, config)
        return
    if action == "favorites":
        await safe_callback_answer(callback)
        from .favorites import show_favorites

        await show_favorites(callback.message, db, user, config)
        return
    if action == "chats":
        await safe_callback_answer(callback)
        from .chats import show_chats

        await show_chats(callback.message, db, user, config)
        return
    if action == "listings":
        await safe_callback_answer(callback)
        from .listings import show_listings

        await show_listings(callback.message, db, user, config)
        return
    if action == "addpet":
        await safe_callback_answer(callback)
        from .listings import begin_wizard

        await begin_wizard(callback.message, state)
        return
    await safe_callback_answer(callback, "Неизвестное действие. Откройте /menu.")


@router.callback_query(F.data.startswith(prefix("set:")))
async def toggle_notifications(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User | None,
) -> None:
    parts = unpack(callback.data, 2)
    if parts is None or parts[0] != "set":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    enabled = await services.toggle_telegram_notifications(db, user.id)
    await services.set_all_telegram_preferences(db, user.id, enabled)
    await safe_callback_answer(
        callback, "Уведомления включены" if enabled else "Уведомления выключены"
    )
    if callback.message is not None:
        await callback.message.edit_reply_markup(
            reply_markup=settings_keyboard(enabled)
        )


@router.callback_query(F.data.startswith(prefix("buy:")))
async def choose_plan(
    callback: CallbackQuery,
    user: User | None,
) -> None:
    parts = unpack(callback.data, 3)
    if parts is None or parts[0] != "buy":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    await safe_callback_answer(callback)
    if callback.message is not None:
        await callback.message.answer(texts.plan_payment_unavailable_text())


@router.message(F.text == "Меню")
async def reply_menu(
    message: Message,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
    config: BotConfig,
) -> None:
    if not await _guard(message, user, state, config) or user is None:
        return
    await state.clear()
    await send_main_menu(message, user, db, config)
