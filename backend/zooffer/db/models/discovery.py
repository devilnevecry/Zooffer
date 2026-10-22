from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, UUIDPrimaryKey


class Swipe(Base, UUIDPrimaryKey):
    __tablename__ = "swipes"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_kind: Mapped[str] = mapped_column(String(16), default="listing", nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    animal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="web", nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    consumed_quota: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "target_kind", "target_id", name="uq_swipes_user_target"),
        UniqueConstraint("user_id", "request_id", name="uq_swipes_user_request"),
        CheckConstraint("action in ('like','skip')", name="action_valid"),
        Index("ix_swipes_animal_action", "animal_id", "action"),
        Index("ix_swipes_user_created", "user_id", "created_at"),
    )


class Favorite(Base, UUIDPrimaryKey):
    __tablename__ = "favorites"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),)


class Match(Base, UUIDPrimaryKey):
    """Mutual like between two animals (mating / pedigree breeding only)."""

    __tablename__ = "matches"

    animal_a_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    animal_b_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_a_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_b_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("animal_a_id", "animal_b_id", name="uq_matches_pair"),
        CheckConstraint("animal_a_id < animal_b_id", name="canonical_order"),
        CheckConstraint("owner_a_id <> owner_b_id", name="distinct_owners"),
    )
