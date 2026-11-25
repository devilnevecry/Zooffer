from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Organization(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "organizations"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    org_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)

    __table_args__ = (
        Index("ix_organizations_status_city", "status", "city_id"),
        Index("ix_organizations_type_status", "org_type", "status"),
    )
