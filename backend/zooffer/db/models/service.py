from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class ServiceProfile(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "service_profiles"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"))
    price_from_kopecks: Mapped[int | None] = mapped_column(Integer)
    formats: Mapped[list[str]] = mapped_column(default=list)
    experience_years: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rating_avg: Mapped[float | None] = mapped_column(Numeric(3, 2))
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_service_profiles_user_category"),
        Index("ix_service_profiles_status_city", "status", "city_id"),
        Index("ix_service_profiles_category_status", "category", "status"),
    )


class ServiceReview(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "service_reviews"

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    booking_ref: Mapped[str | None] = mapped_column(String(80))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("profile_id", "author_id", name="uq_service_reviews_profile_author"),
    )
