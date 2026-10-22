from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey

SEARCH_VECTOR_SQL = (
    "to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || "
    "coalesce(breed_text, ''))"
)


class Listing(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "listings"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    animal_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    breed_text: Mapped[str | None] = mapped_column(String(120))
    price_kopecks: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id", ondelete="SET NULL"))
    city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id", ondelete="SET NULL"), index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderation_reason: Mapped[str | None] = mapped_column(String(400))
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    favorites_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(SEARCH_VECTOR_SQL, persisted=True),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "purpose in ('sale','mating','breeding_pedigree','adoption','rehoming')",
            name="purpose_valid",
        ),
        CheckConstraint(
            "status in ('draft','pending_moderation','published','paused','expired','sold',"
            "'archived','rejected')",
            name="status_valid",
        ),
        CheckConstraint("price_kopecks is null or price_kopecks >= 0", name="price_non_negative"),
        Index("ix_listings_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_listings_public_feed", "status", "purpose", "published_at"),
        Index("ix_listings_city_status", "city_id", "status"),
        Index("ix_listings_price", "price_kopecks"),
    )
