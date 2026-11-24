from __future__ import annotations

import asyncio
import html
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from zooffer.core.utils import utcnow
from zooffer.db.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    Plan,
    Subscription,
    TelegramChat,
    User,
)
from zooffer.db.session import SessionLocal
from zooffer.services import notification_service

from .config import BotConfig

logger = logging.getLogger("zooffer.bot.notifications")

MAX_ATTEMPTS = 5
DELIVERY_CHANNEL = "telegram"


@dataclass(slots=True)
class DeliveryOutcome:
    sent: int = 0
    deferred: int = 0
    skipped: int = 0
    failed: int = 0


def _quiet_now(user: User, preference: NotificationPreference | None, now: datetime) -> bool:
    if preference is None:
        return False
    start, end = preference.quiet_from, preference.quiet_to
    if start is None or end is None or start == end:
        return False
    try:
        tz = ZoneInfo(user.timezone or "Europe/Moscow")
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("Europe/Moscow")
    hour = now.astimezone(tz).hour
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _notification_text(notification: Notification) -> str:
    title = html.escape(notification.title)
    body = html.escape(notification.body or "")
    return f"<b>{title}</b>\n\n{body}" if body else f"<b>{title}</b>"


def _notification_keyboard(
    notification: Notification, config: BotConfig
) -> InlineKeyboardMarkup | None:
    data = notification.data or {}
    renewal_url = data.get("renewal_url")
    if renewal_url:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⏳ Продлить подписку", url=str(renewal_url))]
            ]
        )
    if not config.mini_app_url.startswith("https://"):
        return None
    conversation_id = data.get("conversation_public_id")
    listing_slug = data.get("listing_slug")
    if conversation_id:
        url = f"{config.mini_app_url}/chats/{conversation_id}"
        label = "Открыть чат"
    elif listing_slug:
        url = f"{config.mini_app_url}/listing/{listing_slug}"
        label = "Открыть объявление"
    else:
        url = config.mini_app_url
        label = "Открыть Zooffer"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, url=url)]])


async def _get_or_create_delivery(
    db: AsyncSession, notification_id, existing: NotificationDelivery | None
) -> NotificationDelivery:
    if existing is not None:
        return existing
    delivery = NotificationDelivery(
        notification_id=notification_id,
        channel=DELIVERY_CHANNEL,
        status="pending",
    )
    db.add(delivery)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        delivery = await db.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification_id,
                NotificationDelivery.channel == DELIVERY_CHANNEL,
            )
        )
        if delivery is None:
            raise
    return delivery


async def run_once(
    db: AsyncSession,
    bot: Bot,
    config: BotConfig,
    *,
    now: datetime | None = None,
    limit: int = 20,
) -> DeliveryOutcome:
    """Deliver pending Telegram notifications, honouring preferences quietly.

    A ``NotificationDelivery`` row is created per notification/channel, so a
    repeated run cannot send the same message twice even after a partial failure.
    """
    current = now or utcnow()
    cutoff = current - timedelta(hours=config.notification_max_age_hours)
    rows = (
        await db.execute(
            select(Notification, TelegramChat, User, NotificationDelivery)
            .join(TelegramChat, TelegramChat.user_id == Notification.user_id)
            .join(User, User.id == Notification.user_id)
            .outerjoin(
                NotificationDelivery,
                and_(
                    NotificationDelivery.notification_id == Notification.id,
                    NotificationDelivery.channel == DELIVERY_CHANNEL,
                ),
            )
            .where(
                Notification.created_at >= cutoff,
                TelegramChat.notifications_enabled.is_(True),
                User.status == "active",
                or_(
                    NotificationDelivery.id.is_(None),
                    and_(
                        NotificationDelivery.status.in_(("pending", "deferred")),
                        NotificationDelivery.attempts < MAX_ATTEMPTS,
                    ),
                ),
            )
            .order_by(Notification.created_at)
            .limit(limit)
        )
    ).all()

    outcome = DeliveryOutcome()
    for notification, chat, user, existing in rows:
        preference = await db.get(
            NotificationPreference, (notification.user_id, notification.category)
        )
        delivery = await _get_or_create_delivery(db, notification.id, existing)

        if preference is not None and not preference.telegram:
            delivery.status = "skipped"
            delivery.last_error = "preference_disabled"
            await db.commit()
            outcome.skipped += 1
            continue
        if _quiet_now(user, preference, current):
            delivery.status = "deferred"
            delivery.last_error = "quiet_hours"
            await db.commit()
            outcome.deferred += 1
            continue

        delivery.attempts = (delivery.attempts or 0) + 1
        try:
            await bot.send_message(
                chat_id=chat.chat_id,
                text=_notification_text(notification),
                reply_markup=_notification_keyboard(notification, config),
            )
        except TelegramForbiddenError:
            chat.notifications_enabled = False
            delivery.status = "failed"
            delivery.last_error = "bot_blocked"
            await db.commit()
            outcome.failed += 1
            logger.info("bot_notification_blocked", extra={"notification_id": str(notification.id)})
        except TelegramRetryAfter as exc:
            delivery.status = "deferred"
            delivery.last_error = f"retry_after:{exc.retry_after}"[:400]
            await db.commit()
            outcome.deferred += 1
            logger.warning(
                "bot_notification_flood_wait",
                extra={"retry_after": exc.retry_after},
            )
            if exc.retry_after <= 30:
                await asyncio.sleep(exc.retry_after)
        except TelegramBadRequest as exc:
            delivery.status = "failed"
            delivery.last_error = str(exc)[:400]
            await db.commit()
            outcome.failed += 1
            logger.warning(
                "bot_notification_bad_request",
                extra={"notification_id": str(notification.id)},
            )
        except Exception as exc:
            delivery.status = "failed" if delivery.attempts >= MAX_ATTEMPTS else "pending"
            delivery.last_error = str(exc)[:400]
            await db.commit()
            outcome.failed += 1
            logger.exception("bot_notification_error")
        else:
            delivery.status = "sent"
            delivery.sent_at = current
            delivery.last_error = None
            await db.commit()
            outcome.sent += 1
    return outcome


async def run_subscription_reminders(db: AsyncSession, config: BotConfig) -> int:
    """Create one 3-day and one 1-day renewal reminder per paid period."""
    now = utcnow()
    rows = (
        await db.execute(
            select(Subscription, Plan)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.status.in_(["active", "past_due"]),
                Subscription.current_period_end.is_not(None),
                Subscription.current_period_end > now,
                Subscription.current_period_end <= now + timedelta(days=3),
            )
        )
    ).all()
    created = 0
    for subscription, plan in rows:
        end = subscription.current_period_end
        assert end is not None
        seconds_left = int((end - now).total_seconds())
        days_left = max(1, -(-seconds_left // 86400))
        if days_left not in (1, 3):
            continue
        existing = await db.scalar(
            select(Notification.id).where(
                Notification.user_id == subscription.user_id,
                Notification.category == "subscriptions",
                Notification.created_at >= now - timedelta(days=5),
                Notification.data["reminder_days"].astext == str(days_left),
                Notification.data["plan_code"].astext == plan.code,
            )
        )
        if existing is not None:
            continue
        notification_service.subscription_expiry_reminder(
            db,
            user_id=subscription.user_id,
            plan_code=plan.code,
            plan_name=plan.name,
            days_left=days_left,
            renewal_url=f"https://t.me/{config.bot_username}?start=buy_{plan.code}",
        )
        created += 1
    if created:
        await db.commit()
    return created


async def run_worker(bot: Bot, config: BotConfig) -> None:
    interval = max(config.notification_interval_seconds, 5)
    reminder_interval = max(config.reminder_check_interval_seconds, 60)
    logger.info("bot_notification_worker_started", extra={"interval": interval})
    last_reminder_check = datetime.min.replace(tzinfo=UTC)
    while True:
        try:
            async with SessionLocal() as session:
                current = utcnow()
                if (current - last_reminder_check).total_seconds() >= reminder_interval:
                    created = await run_subscription_reminders(session, config)
                    if created:
                        logger.info("subscription_reminders_created", extra={"count": created})
                    last_reminder_check = current
                outcome = await run_once(session, bot, config, limit=config.notification_batch_size)
                if outcome.sent or outcome.deferred or outcome.failed:
                    logger.info(
                        "bot_notifications_delivered",
                        extra={
                            "sent": outcome.sent,
                            "deferred": outcome.deferred,
                            "skipped": outcome.skipped,
                            "failed": outcome.failed,
                        },
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("bot_notification_worker_error")
        await asyncio.sleep(interval)


def utc_now() -> datetime:
    """Small helper kept for tests that need the same clock as the worker."""
    return datetime.now(UTC)
