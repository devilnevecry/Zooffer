from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Place(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "places"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    reporter_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    moderation_reason: Mapped[str | None] = mapped_column(String(400))
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        CheckConstraint(
            "category in ('vet_clinic','groomer','park','cafe','dangerous','shelter','other')",
            name="place_category_valid",
        ),
        CheckConstraint("status in ('pending','approved','rejected')", name="place_status_valid"),
        Index("ix_places_status_geo", "status", "latitude", "longitude"),
        Index("ix_places_category_status", "category", "status"),
    )
