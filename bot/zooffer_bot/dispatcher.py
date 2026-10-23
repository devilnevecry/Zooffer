from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    ErrorEvent,
    MenuButtonWebApp,
    WebAppInfo,
)
from zooffer.config import settings

from .config import BotConfig
from .handlers import ROUTERS

logger = logging.getLogger("zooffer.bot")

BOT_COMMANDS = (
    ("start", "Начать и открыть меню"),
    ("menu", "Главное меню"),
    ("swipe", "Подбор питомцев"),
    ("favorites", "Избранное"),
    ("chats", "Сообщения"),
    ("mylistings", "Мои объявления"),
    ("addpet", "Добавить объявление"),
    ("subscription", "Подписка"),
    ("buy", "Купить подписку"),
    ("support", "Поддержка"),
    ("profile", "Профиль"),
    ("settings", "Настройки уведомлений"),
    ("news", "Новости Zooffer"),
    ("link", "Привязать аккаунт"),
    ("language", "Язык"),
    ("paysupport", "Поддержка по оплате"),
    ("stop", "Отключить уведомления"),
    ("cancel", "Отменить действие"),
    ("help", "Помощь"),
)


def _build_storage(config: BotConfig) -> BaseStorage:
    """Redis-backed FSM with TTL in every environment except tests.

    A Redis outage must not silently downgrade production to per-process state, so the
    caller gets a clear error there. Local development may continue with memory storage.
    """
    if settings.environment == "test":
        return MemoryStorage()
    if not config.redis_url:
        if settings.environment in {"dev"}:
            logger.warning("bot_fsm_memory_fallback", extra={"reason": "no redis url"})
            return MemoryStorage()
        raise RuntimeError("REDIS_URL is required for the Telegram bot FSM")
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        from redis.asyncio import Redis

        client = Redis.from_url(config.redis_url, decode_responses=True)
        return RedisStorage(
            client,
            state_ttl=config.fsm_ttl_seconds,
            data_ttl=config.fsm_ttl_seconds,
        )
    except Exception as exc:  # pragma: no cover - depends on infrastructure
        if settings.environment in {"dev"}:
            logger.warning("bot_fsm_memory_fallback", extra={"reason": str(exc)})
            return MemoryStorage()
        raise


async def _on_error(event: ErrorEvent) -> None:
    exc = event.exception
    update_id = event.update.update_id if event.update is not None else None
    if isinstance(exc, TelegramForbiddenError):
        # The user blocked the bot or the chat was deleted. Do not retry.
        logger.info("bot_forbidden", extra={"update_id": update_id})
        return
    if isinstance(exc, TelegramRetryAfter):
        logger.warning(
            "bot_flood_wait",
            extra={"update_id": update_id, "retry_after": exc.retry_after},
        )
        return
    if isinstance(exc, TelegramBadRequest):
        logger.warning(
            "bot_bad_request",
            extra={"update_id": update_id, "error": str(exc)[:300]},
        )
        return
    logger.exception("bot_handler_error", extra={"update_id": update_id})


def build_dispatcher(config: BotConfig, *, storage: BaseStorage | None = None) -> Dispatcher:
    """Create a dispatcher with shared middlewares, routers and error handling.

    ``config`` is injected into every handler through aiogram's workflow data, so
    handlers never read process environment directly.
    """
    from .middlewares import BotUserMiddleware, DatabaseMiddleware, ThrottleMiddleware

    dp = Dispatcher(storage=storage or _build_storage(config), config=config)
    dp.errors.register(_on_error)

    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(DatabaseMiddleware())
        observer.outer_middleware(BotUserMiddleware())
        observer.outer_middleware(ThrottleMiddleware(config))

    dp.include_routers(*ROUTERS)
    return dp


async def setup_bot(bot: Bot, config: BotConfig) -> None:
    """Publish commands and the persistent Mini App menu button.

    Telegram only accepts HTTPS Web Apps, so local HTTP development keeps the reply
    keyboard entry point and the bot still works without it.
    """
    await bot.set_my_commands(
        [BotCommand(command=name, description=description) for name, description in BOT_COMMANDS],
        scope=BotCommandScopeDefault(),
    )
    if config.mini_app_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть Zooffer",
                web_app=WebAppInfo(url=config.mini_app_url),
            )
        )
    else:
        logger.info("bot_menu_button_skipped", extra={"reason": "mini app url is not https"})
