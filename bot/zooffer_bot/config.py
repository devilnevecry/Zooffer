from __future__ import annotations

import os
from dataclasses import dataclass

from zooffer.config import settings


@dataclass(frozen=True, slots=True)
class BotConfig:
    token: str
    webhook_secret: str
    webhook_url: str
    webhook_path: str
    redis_url: str
    mode: str
    public_url: str
    channel_url: str
    mini_app_url: str
    bot_username: str
    fsm_ttl_seconds: int
    update_queue: str
    update_workers: int
    throttle_limit: int
    throttle_window: int
    global_throttle_limit: int
    global_throttle_window: int
    webhook_host: str
    webhook_port: int
    notification_worker: bool
    notification_interval_seconds: int
    notification_batch_size: int
    notification_max_age_hours: int


def load_config() -> BotConfig:
    public_url = os.getenv("BOT_PUBLIC_URL", settings.app_base_url).rstrip("/")
    username = os.getenv("TELEGRAM_BOT_USERNAME", settings.telegram_bot_username).lstrip("@")
    return BotConfig(
        token=os.getenv("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token),
        webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", settings.telegram_webhook_secret),
        webhook_url=os.getenv("TELEGRAM_WEBHOOK_URL", ""),
        webhook_path=os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook"),
        redis_url=os.getenv("REDIS_URL", settings.redis_url),
        mode=os.getenv("BOT_MODE", "webhook").lower(),
        public_url=public_url,
        channel_url=os.getenv("TELEGRAM_CHANNEL_URL", ""),
        mini_app_url=f"{public_url}/tg",
        bot_username=username,
        fsm_ttl_seconds=int(os.getenv("BOT_FSM_TTL_SECONDS", "3600")),
        update_queue=os.getenv("BOT_UPDATE_QUEUE", "inline").lower(),
        update_workers=max(int(os.getenv("BOT_UPDATE_WORKERS", "1")), 1),
        throttle_limit=int(os.getenv("BOT_THROTTLE_LIMIT", "25")),
        throttle_window=int(os.getenv("BOT_THROTTLE_WINDOW", "10")),
        global_throttle_limit=int(os.getenv("BOT_GLOBAL_THROTTLE_LIMIT", "200")),
        global_throttle_window=int(os.getenv("BOT_GLOBAL_THROTTLE_WINDOW", "10")),
        # Container bind: the bot listens behind a reverse proxy, not on a public host port.
        webhook_host=os.getenv("BOT_WEBHOOK_HOST", "0.0.0.0"),  # noqa: S104  # nosec B104
        webhook_port=int(os.getenv("BOT_WEBHOOK_PORT", "8081")),
        notification_worker=os.getenv("BOT_NOTIFICATION_WORKER", "true").lower()
        in {"1", "true", "yes", "on"},
        notification_interval_seconds=int(os.getenv("BOT_NOTIFICATION_INTERVAL", "15")),
        notification_batch_size=int(os.getenv("BOT_NOTIFICATION_BATCH", "20")),
        notification_max_age_hours=int(os.getenv("BOT_NOTIFICATION_MAX_AGE_HOURS", "24")),
    )


def require_bot_token(config: BotConfig) -> str:
    if not config.token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured; the bot cannot start. See docs/BLOCKERS.md (B2)."
        )
    return config.token


def require_webhook_secret(config: BotConfig) -> str:
    if not config.webhook_secret:
        raise RuntimeError(
            "TELEGRAM_WEBHOOK_SECRET is not configured; the webhook refuses to start. "
            "See docs/BLOCKERS.md (B2)."
        )
    return config.webhook_secret
