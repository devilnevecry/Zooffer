from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from zooffer.core.enums import Entitlement
from zooffer.core.errors import QuotaExceededError
from zooffer.core.metrics import QUOTA_REJECTIONS
from zooffer.core.utils import next_quota_reset, quota_date
from zooffer.db.models import DailyQuotaUsage, QuotaEvent
from zooffer.services.entitlements import daily_swipe_limit, get_entitlements


class QuotaStatus:
    def __init__(self, *, limit: int, used: int, unlimited: bool, resets_at) -> None:
        self.limit = limit
        self.used = used
        self.unlimited = unlimited
        self.resets_at = resets_at

    @property
    def remaining(self) -> int:
        if self.unlimited:
            return 0
        return max(self.limit - self.used, 0)


async def get_quota(db: AsyncSession, user_id: UUID) -> QuotaStatus:
    limit, unlimited = await daily_swipe_limit(db, user_id)
    qdate = quota_date()
    used = await db.scalar(
        select(DailyQuotaUsage.used_count).where(
            DailyQuotaUsage.user_id == user_id, DailyQuotaUsage.quota_date == qdate
        )
    )
    return QuotaStatus(
        limit=0 if unlimited else limit,
        used=used or 0,
        unlimited=unlimited,
        resets_at=next_quota_reset(),
    )


async def consume_quota(
    db: AsyncSession, user_id: UUID, *, reason: str = "swipe", swipe_id: UUID | None = None
) -> QuotaStatus:
    """Atomically consume one unit.

    Must be called inside the same transaction as the swipe insert. Uses a conditional
    upsert so concurrent requests can never exceed the limit.
    """
    limit, unlimited = await daily_swipe_limit(db, user_id)
    qdate = quota_date()
    stmt = pg_insert(DailyQuotaUsage).values(user_id=user_id, quota_date=qdate, used_count=1)
    if unlimited:
        stmt = stmt.on_conflict_do_update(
            index_elements=[DailyQuotaUsage.user_id, DailyQuotaUsage.quota_date],
            set_={"used_count": DailyQuotaUsage.used_count + 1},
        )
    else:
        stmt = stmt.on_conflict_do_update(
            index_elements=[DailyQuotaUsage.user_id, DailyQuotaUsage.quota_date],
            set_={"used_count": DailyQuotaUsage.used_count + 1},
            where=DailyQuotaUsage.used_count < limit,
        )
    result = await db.execute(stmt.returning(DailyQuotaUsage.used_count))
    used = result.scalar_one_or_none()
    if used is None:
        QUOTA_REJECTIONS.inc()
        raise QuotaExceededError(
            "Дневной лимит показов закончился. Откройте подписку или возвращайтесь после полуночи.",
            details={"resets_at": next_quota_reset().isoformat(), "limit": limit},
        )
    db.add(
        QuotaEvent(
            user_id=user_id,
            quota_date=qdate,
            delta=1,
            reason=reason,
            swipe_id=swipe_id,
            limit_at_time=None if unlimited else limit,
        )
    )
    return QuotaStatus(
        limit=0 if unlimited else limit,
        used=used,
        unlimited=unlimited,
        resets_at=next_quota_reset(),
    )


async def restore_quota(db: AsyncSession, user_id: UUID, *, reason: str = "undo") -> None:
    qdate: date = quota_date()
    row = await db.scalar(
        select(DailyQuotaUsage)
        .where(DailyQuotaUsage.user_id == user_id, DailyQuotaUsage.quota_date == qdate)
        .with_for_update()
    )
    if row is not None and row.used_count > 0:
        row.used_count -= 1
    db.add(QuotaEvent(user_id=user_id, quota_date=qdate, delta=-1, reason=reason))


async def has_undo_entitlement(db: AsyncSession, user_id: UUID) -> bool:
    return Entitlement.UNDO in await get_entitlements(db, user_id)
