from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.utils import utcnow
from zooffer.db.models import EntitlementGrant, Plan, Subscription, SystemSetting


async def get_setting(db: AsyncSession, key: str, default: object = None) -> object:
    setting = await db.get(SystemSetting, key)
    if setting is None:
        return default
    if isinstance(setting.value, dict) and "value" in setting.value:
        return setting.value["value"]
    return setting.value


async def set_setting(db: AsyncSession, key: str, value: object, actor_id: UUID | None) -> None:
    setting = await db.get(SystemSetting, key)
    payload = {"value": value}
    if setting is None:
        db.add(SystemSetting(key=key, value=payload, updated_by=actor_id))
    else:
        setting.value = payload
        setting.updated_by = actor_id
    await db.commit()


async def get_entitlements(db: AsyncSession, user_id: UUID) -> set[str]:
    now = utcnow()
    codes: set[str] = set()
    rows = await db.execute(
        select(Plan.entitlements)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "past_due"]),
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end > now,
            Plan.is_active.is_(True),
        )
    )
    for entitlements in rows.scalars():
        codes.update(entitlements or [])
    grants = await db.execute(
        select(EntitlementGrant.code).where(
            EntitlementGrant.user_id == user_id,
            (EntitlementGrant.expires_at.is_(None)) | (EntitlementGrant.expires_at > now),
        )
    )
    codes.update(grants.scalars())
    return codes


async def daily_swipe_limit(db: AsyncSession, user_id: UUID) -> tuple[int, bool]:
    """Returns (limit, unlimited). A negative limit means unlimited."""
    entitlements = await get_entitlements(db, user_id)
    if "unlimited_swipes" in entitlements:
        return -1, True
    configured = await get_setting(db, "free_daily_swipes", None)
    value = configured if isinstance(configured, int) else None
    if value is None:
        from zooffer.config import settings

        value = settings.free_daily_swipes
    return max(int(value), 0), False


def subscription_active(subscription: Subscription, now: datetime | None = None) -> bool:
    current = now or utcnow()
    return bool(
        subscription.status in {"active", "past_due"}
        and subscription.current_period_end
        and subscription.current_period_end > current
    )
