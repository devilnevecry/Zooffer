from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from zooffer.db.models import BotUpdateSeen
from zooffer.db.session import SessionLocal

from .config import BotConfig, require_webhook_secret

logger = logging.getLogger("zooffer.bot.webhook")

# HTTP header name carrying the Telegram webhook secret, not a secret value.
SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"  # noqa: S105  # nosec B105
MAX_UPDATE_BYTES = 1024 * 1024


async def claim_update(update_id: int) -> bool:
    """Atomically claim an update_id. Returns False for a Telegram retry."""
    async with SessionLocal() as session:
        session.add(BotUpdateSeen(update_id=update_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return False
    return True


async def release_update(update_id: int) -> None:
    """Return a claimed update to Telegram after we could not enqueue it."""
    async with SessionLocal() as session:
        row = await session.get(BotUpdateSeen, update_id)
        if row is not None:
            await session.delete(row)
            await session.commit()


async def prune_seen_updates(older_than_days: int = 7) -> None:
    """Keep the dedupe table bounded; Telegram never retries updates this old."""
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    async with SessionLocal() as session:
        await session.execute(delete(BotUpdateSeen).where(BotUpdateSeen.seen_at < cutoff))
        await session.commit()


class UpdateQueue:
    """Bounded in-process update queue.

    Telegram receives an immediate 200 after the update is queued. The queue is
    deliberately small and single-consumer so per-chat FSM updates stay ordered.
    A process restart can lose queued updates; Telegram retries only when it does
    not receive a 200, which is why the durable-queue item is tracked in
    docs/KNOWN_ISSUES.md.
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        *,
        maxsize: int = 512,
        workers: int = 1,
    ) -> None:
        self._dispatcher = dispatcher
        self._bot = bot
        self._queue: asyncio.Queue[Update] = asyncio.Queue(maxsize=maxsize)
        self._workers = [asyncio.create_task(self._run()) for _ in range(max(1, workers))]
        self._stopping = False

    async def put(self, update: Update) -> bool:
        try:
            self._queue.put_nowait(update)
        except asyncio.QueueFull:
            return False
        return True

    async def _run(self) -> None:
        while True:
            update = await self._queue.get()
            try:
                await self._dispatcher.feed_update(self._bot, update)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("bot_queued_update_failed", extra={"update_id": update.update_id})
            finally:
                self._queue.task_done()

    async def stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)


def create_webhook_app(
    dispatcher: Dispatcher,
    bot: Bot,
    config: BotConfig,
    *,
    update_queue: UpdateQueue | None = None,
) -> FastAPI:
    """Build the FastAPI application that receives Telegram updates.

    The secret header is verified before any parsing or database access. Updates
    are deduplicated by ``update_id`` and either processed inline or queued.
    """
    secret = require_webhook_secret(config)
    queue = update_queue

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if queue is not None:
            await queue.stop()
        yield
        if queue is not None:
            await queue.stop()
        close_storage = getattr(dispatcher.storage, "close", None)
        if close_storage is not None:
            await close_storage()
        await bot.session.close()

    app = FastAPI(
        title="Zooffer Telegram webhook",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(config.webhook_path)
    async def telegram_webhook(request: Request) -> JSONResponse:
        supplied = request.headers.get(SECRET_HEADER, "")
        if not hmac.compare_digest(supplied, secret):
            logger.warning("bot_webhook_forbidden", extra={"path": request.url.path})
            return JSONResponse({"ok": False}, status_code=403)

        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > MAX_UPDATE_BYTES:
                    return JSONResponse({"ok": False}, status_code=413)
            except ValueError:
                return JSONResponse({"ok": False}, status_code=400)

        raw = await request.body()
        if len(raw) > MAX_UPDATE_BYTES:
            return JSONResponse({"ok": False}, status_code=413)
        try:
            update = Update.model_validate_json(raw)
        except ValidationError:
            logger.warning("bot_webhook_invalid_payload")
            return JSONResponse({"ok": False}, status_code=400)

        if not await claim_update(update.update_id):
            logger.info("bot_update_duplicate", extra={"update_id": update.update_id})
            return JSONResponse({"ok": True, "duplicate": True})

        if update.update_id % 500 == 0:
            await prune_seen_updates()

        if queue is not None and config.update_queue != "inline":
            if not await queue.put(update):
                await release_update(update.update_id)
                logger.warning("bot_update_queue_full", extra={"update_id": update.update_id})
                return JSONResponse({"ok": False}, status_code=503)
            return JSONResponse({"ok": True, "queued": True})

        await dispatcher.feed_update(bot, update)
        return JSONResponse({"ok": True})

    return app


async def run_webhook(
    dispatcher: Dispatcher,
    bot: Bot,
    config: BotConfig,
    *,
    # The webhook container binds to all interfaces; the reverse proxy exposes HTTPS only.
    host: str = "0.0.0.0",  # noqa: S104  # nosec B104
    port: int = 8081,
    workers: int = 1,
) -> None:
    """Serve the webhook with uvicorn until cancelled."""
    import uvicorn

    queue = UpdateQueue(dispatcher, bot, workers=workers)
    app = create_webhook_app(dispatcher, bot, config, update_queue=queue)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level=settings_log_level(),
            access_log=False,
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
    )
    logger.info("bot_webhook_starting", extra={"host": host, "port": port})
    await server.serve()


def settings_log_level() -> str:
    from zooffer.config import settings

    return settings.log_level.lower()


__all__: list[str] = [
    "SECRET_HEADER",
    "UpdateQueue",
    "claim_update",
    "create_webhook_app",
    "prune_seen_updates",
    "release_update",
    "run_webhook",
]
