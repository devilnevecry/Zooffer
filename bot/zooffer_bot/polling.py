from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import BotConfig

logger = logging.getLogger("zooffer.bot.polling")


async def run_polling(dispatcher: Dispatcher, bot: Bot, config: BotConfig) -> None:
    """Long polling for local development only.

    Production uses the webhook entry point in ``webhook.py``. Deleting the
    webhook first prevents a ``409 Conflict`` if the same token was previously
    registered with Telegram.
    """
    if config.mode != "polling":
        raise RuntimeError("run_polling called outside BOT_MODE=polling")
    await bot.delete_webhook(drop_pending_updates=False)
    allowed_updates = dispatcher.resolve_used_update_types()
    logger.info("bot_polling_started", extra={"allowed_updates": allowed_updates})
    try:
        await dispatcher.start_polling(bot, allowed_updates=allowed_updates)
    except asyncio.CancelledError:
        logger.info("bot_polling_stopped")
        raise
