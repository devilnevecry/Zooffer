from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.errors import RateLimitedError
from zooffer.core.rate_limit import limiter
from zooffer.db.session import SessionLocal
from zooffer.services import auth_service

from .config import BotConfig

logger = logging.getLogger("zooffer.bot.middlewares")


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with SessionLocal() as session:
            data["db"] = session
            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise


class BotUserMiddleware(BaseMiddleware):
    """Resolve a Telegram ID to the canonical Zooffer user.

    Handlers receive ``user=None`` for new chats; onboarding creates the account
    only after explicit consent and a chosen public name.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TelegramUser | None = data.get("event_from_user")
        db: AsyncSession = data["db"]
        user = None
        if tg_user is not None:
            user = await auth_service.find_telegram_user(db, str(tg_user.id))
        data["user"] = user
        data["tg_user"] = tg_user
        data["telegram_id"] = str(tg_user.id) if tg_user is not None else None
        return await handler(event, data)


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = data.get("telegram_id")
        if not telegram_id:
            return await handler(event, data)
        try:
            await limiter.hit(
                "bot:global",
                limit=self.config.global_throttle_limit,
                window_seconds=self.config.global_throttle_window,
            )
        except RateLimitedError:
            logger.warning("bot_global_throttle", extra={"telegram_id": telegram_id})
            return None
        try:
            await limiter.hit(
                f"bot:{telegram_id}",
                limit=self.config.throttle_limit,
                window_seconds=self.config.throttle_window,
            )
        except RateLimitedError as exc:
            message = f"Слишком много действий. Повторите через {exc.retry_after} с."
            if isinstance(event, CallbackQuery):
                await event.answer(message, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(message)
            return None
        return await handler(event, data)
