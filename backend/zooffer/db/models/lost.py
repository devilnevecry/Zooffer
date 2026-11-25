from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class LostReport(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "lost_reports"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    reporter_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    animal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("animals.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="searching", index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    last_seen_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    last_seen_description: Mapped[str | None] = mapped_column(String(400))
    radius_km: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    found_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status in ('searching','found','closed')", name="lost_report_status_valid"
        ),
        CheckConstraint("radius_km >= 1 and radius_km <= 100", name="lost_report_radius_valid"),
        Index("ix_lost_reports_status_geo", "status", "last_seen_latitude", "last_seen_longitude"),
    )


class LostSighting(Base, UUIDPrimaryKey):
    __tablename__ = "lost_sightings"

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("lost_reports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reporter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    request_id: Mapped[str | None] = mapped_column(String(64))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(400))
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "reporter_id",
            "request_id",
            name="uq_lost_sightings_report_reporter_request",
        ),
    )
