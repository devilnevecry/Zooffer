from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, UUIDPrimaryKey


class DailyQuotaUsage(Base):
    """Canonical cross-channel quota counter. quota_date is Europe/Moscow local date."""

    __tablename__ = "daily_quota_usage"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    quota_date: Mapped[date] = mapped_column(Date, primary_key=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (CheckConstraint("used_count >= 0", name="used_non_negative"),)


class QuotaEvent(Base, UUIDPrimaryKey):
    __tablename__ = "quota_events"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quota_date: Mapped[date] = mapped_column(Date, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    swipe_id: Mapped[UUID | None] = mapped_column(ForeignKey("swipes.id", ondelete="SET NULL"))
    limit_at_time: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    __table_args__ = (Index("ix_quota_events_user_date", "user_id", "quota_date"),)
