from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from zooffer.config import settings
from zooffer.core.logging import configure_logging

from .config import load_config, require_bot_token
from .dispatcher import build_dispatcher, setup_bot
from .notifications import run_worker
from .polling import run_polling
from .webhook import run_webhook

logger = logging.getLogger("zooffer.bot")


async def async_main() -> None:
    configure_logging(settings.log_level)
    config = load_config()
    token = require_bot_token(config)
    bot = Bot(
        token=token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
    dispatcher = build_dispatcher(config)
    worker_task: asyncio.Task[None] | None = None
    if config.notification_worker:
        worker_task = asyncio.create_task(run_worker(bot, config))
    try:
        await setup_bot(bot, config)
        if config.mode == "polling":
            await run_polling(dispatcher, bot, config)
            return
        if config.mode != "webhook":
            raise RuntimeError(f"Unknown BOT_MODE={config.mode!r}; use webhook or polling")
        if not config.webhook_url:
            raise RuntimeError(
                "TELEGRAM_WEBHOOK_URL is required for BOT_MODE=webhook. "
                "See docs/BLOCKERS.md (B2) and docs/TELEGRAM.md."
            )
        await bot.set_webhook(
            url=config.webhook_url,
            secret_token=config.webhook_secret,
            allowed_updates=dispatcher.resolve_used_update_types(),
            drop_pending_updates=False,
        )
        await run_webhook(
            dispatcher,
            bot,
            config,
            host=config.webhook_host,
            port=config.webhook_port,
            workers=config.update_workers,
        )
    finally:
        if worker_task is not None:
            worker_task.cancel()
            await asyncio.gather(worker_task, return_exceptions=True)
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:  # pragma: no cover - interactive shutdown
        pass
    except RuntimeError as exc:
        logger.error("bot_startup_failed", extra={"error": str(exc)})
        raise


if __name__ == "__main__":
    main()
