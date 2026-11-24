from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.config import settings
from zooffer.core.errors import AppError
from zooffer.db.models import User

from .. import services, texts
from ..callbacks import prefix, unpack
from ..config import BotConfig
from ..keyboards import (
    back_menu_keyboard,
    crypto_paid_keyboard,
    duration_keyboard,
    main_menu,
    news_keyboard,
    payment_method_keyboard,
    plans_keyboard,
    profile_keyboard,
    settings_keyboard,
    subscription_keyboard,
)
from .common import ensure_onboarded, safe_callback_answer, send_main_menu, show_screen

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
    subscription = await services.get_subscription_view(db, user)
    await message.answer(
        texts.profile_text(name, city, user.role, subscription),
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
        reply_markup=subscription_keyboard(bool(plans), view.status in {"active", "past_due"}),
    )


def _plan_label(plan) -> str:  # type: ignore[no-untyped-def]
    if plan.stars_amount:
        return f"{plan.name} · {plan.stars_amount} Stars / {plan.period_days} дн."
    return f"{plan.name} · {plan.price_kopecks / 100:,.0f} ₽ / {plan.period_days} дн.".replace(
        ",", " "
    )


async def _available_plans(db, user):  # type: ignore[no-untyped-def]
    """Only plans that are an upgrade or a different term, never a downgrade."""
    options = []
    for plan in await services.plan_views(db):
        if plan.price_kopecks <= 0 or not plan.stars_amount:
            continue
        preview = await services.purchase_preview(db, user, plan.code)
        if preview["can_buy"]:
            options.append(plan)
    return options


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
    await state.update_data(renew_plan=None)
    plans = await _available_plans(db, user)
    available = services.payments_available()
    if not plans:
        view = await services.get_subscription_view(db, user)
        await state.update_data(renew_plan=view.plan_code)
        await message.answer(
            texts.best_plan_text(view.plan_name, view.current_period_end),
            reply_markup=duration_keyboard(view.plan_code or "premium", show_other=False),
        )
        return
    await message.answer(
        texts.plans_text(True, available),
        reply_markup=plans_keyboard([(plan.code, _plan_label(plan)) for plan in plans])
        if available
        else main_menu(config.mini_app_url),
    )
    if not available:
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
        name = await services.public_name_for(db, user)
        await show_screen(callback, texts.menu_text(name), main_menu(config.mini_app_url))
        return
    if action == "help":
        await safe_callback_answer(callback)
        await show_screen(callback, texts.help_text(), back_menu_keyboard("home"))
        return
    if action == "profile":
        await safe_callback_answer(callback)
        name = await services.public_name_for(db, user)
        city = await services.city_name_for(db, user)
        subscription = await services.get_subscription_view(db, user)
        await show_screen(
            callback,
            texts.profile_text(name, city, user.role, subscription),
            profile_keyboard(config.mini_app_url),
        )
        return
    if action == "settings":
        await safe_callback_answer(callback)
        enabled = await services.telegram_notifications_enabled(db, user.id)
        await show_screen(callback, texts.settings_text(enabled), settings_keyboard(enabled))
        return
    if action == "subscription":
        await safe_callback_answer(callback)
        view = await services.get_subscription_view(db, user)
        plans = await services.plan_views(db)
        await show_screen(
            callback,
            texts.subscription_text(view),
            subscription_keyboard(bool(plans), view.status in {"active", "past_due"}),
        )
        return
    if action == "buy":
        await state.update_data(renew_plan=None)
        await safe_callback_answer(callback)
        plans = await _available_plans(db, user)
        available = services.payments_available()
        if not plans:
            view = await services.get_subscription_view(db, user)
            await state.update_data(renew_plan=view.plan_code)
            await show_screen(
                callback,
                texts.best_plan_text(view.plan_name, view.current_period_end),
                duration_keyboard(view.plan_code or "premium", show_other=False),
            )
            return
        if not available:
            await show_screen(
                callback, texts.plan_payment_unavailable_text(), back_menu_keyboard("subscription")
            )
            return
        await show_screen(
            callback,
            texts.plans_text(True, True),
            plans_keyboard([(plan.code, _plan_label(plan)) for plan in plans]),
        )
        return
    if action == "renew":
        view = await services.get_subscription_view(db, user)
        if not view.plan_code or view.status not in {"active", "past_due"}:
            await safe_callback_answer(callback, "Активной подписки нет", show_alert=True)
            return
        await state.update_data(renew_plan=view.plan_code)
        await safe_callback_answer(callback)
        await show_screen(
            callback,
            texts.duration_text(view.plan_name or "Текущий тариф", "Продление без новой подписки."),
            duration_keyboard(view.plan_code),
        )
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
    await show_screen(callback, texts.settings_text(enabled), settings_keyboard(enabled))


@router.callback_query(F.data.startswith(prefix("buydur:")))
async def choose_duration(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User | None,
) -> None:
    parts = unpack(callback.data, 3)
    if parts is None or parts[0] != "buydur":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    plan_view = next(
        (p for p in await services.plan_views(db) if p.code == parts[2]),
        None,
    )
    if user is None or plan_view is None:
        await safe_callback_answer(callback, "Тариф не найден. Откройте /buy.", show_alert=True)
        return
    await safe_callback_answer(callback)
    await show_screen(
        callback,
        texts.duration_text(plan_view.name, plan_view.description),
        duration_keyboard(plan_view.code),
    )


@router.callback_query(F.data.startswith(prefix("buy:")))
async def choose_plan(
    callback: CallbackQuery,
    state: FSMContext,
    db: AsyncSession,
    user: User | None,
) -> None:
    parts = unpack(callback.data, 4)
    if parts is None or parts[0] != "buy":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    if not services.payments_available():
        await safe_callback_answer(callback)
        await show_screen(
            callback, texts.plan_payment_unavailable_text(), back_menu_keyboard("subscription")
        )
        return
    try:
        months = int(parts[3])
        renew_plan = (await state.get_data()).get("renew_plan")
        preview = await services.purchase_preview(
            db, user, parts[2], months=months, allow_renew=renew_plan == parts[2]
        )
    except (ValueError, AppError) as exc:
        await safe_callback_answer(callback, str(exc), show_alert=True)
        return
    if not preview["can_buy"]:
        await safe_callback_answer(callback, preview["reason"], show_alert=True)
        return
    await safe_callback_answer(callback)
    await show_screen(
        callback,
        texts.plan_details_text(preview),
        payment_method_keyboard(parts[2], preview["charge_stars"], months=months),
    )


@router.callback_query(F.data.startswith(prefix("buystars:")))
async def choose_stars_plan(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User | None,
    bot: Bot,
) -> None:
    """Final step: send a Telegram Stars invoice for the selected plan and term."""
    parts = unpack(callback.data, 4)
    if parts is None or parts[0] != "buystars":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    if callback.message is None:
        await safe_callback_answer(callback)
        return
    preview = await services.purchase_preview(db, user, parts[2], months=int(parts[3]))
    if not preview["can_buy"]:
        await safe_callback_answer(callback, preview["reason"], show_alert=True)
        return
    try:
        order, plan = await services.prepare_stars_order(db, user, parts[2], months=int(parts[3]))
    except AppError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    await safe_callback_answer(callback)
    if not order.stars_amount:
        await show_screen(
            callback, texts.plan_payment_unavailable_text(), back_menu_keyboard("subscription")
        )
        return
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=plan.name,
        description=(
            f"{plan.description[:200]} · {int(parts[3])} мес. "
            f"({preview['total_days']} дней с учётом текущей подписки)"
        )[:255],
        payload=f"stars:{order.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan.name[:32], amount=order.stars_amount)],
    )


@router.callback_query(F.data.startswith(prefix("buycrypto:")))
async def choose_crypto_plan(
    callback: CallbackQuery,
    db: AsyncSession,
    user: User | None,
) -> None:
    """Final step: show wallet details for an off-chain crypto transfer."""
    parts = unpack(callback.data, 4)
    if parts is None or parts[0] != "buycrypto":
        await safe_callback_answer(callback, "Кнопка устарела.")
        return
    plan_code = parts[2]
    if user is None:
        await safe_callback_answer(callback, "Сначала отправьте /start.")
        return
    if callback.message is None:
        await safe_callback_answer(callback)
        return
    try:
        order, plan = await services.prepare_crypto_order(db, user, plan_code, months=int(parts[3]))
    except AppError as exc:
        await safe_callback_answer(callback, exc.message, show_alert=True)
        return
    await safe_callback_answer(callback)
    await show_screen(
        callback,
        texts.crypto_payment_text(
            plan_name=plan.name,
            amount=order.amount_kopecks / 100,
            currency=order.currency,
            wallet=settings.crypto_payment_wallet_address,
            asset=settings.crypto_payment_asset,
            network=settings.crypto_payment_network,
            order_id=str(order.id),
        ),
        crypto_paid_keyboard(),
    )


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
