from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, UUIDPrimaryKey


class AnimalCoOwner(Base, UUIDPrimaryKey):
    __tablename__ = "animal_co_owners"

    animal_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(24), default="co_owner", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("animal_id", "user_id", name="uq_animal_co_owners_animal_user"),
    )
