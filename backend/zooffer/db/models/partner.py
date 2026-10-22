from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Partner(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "partners"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    logo_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)

    __table_args__ = (
        CheckConstraint("status in ('draft','active','paused','archived')", name="status_valid"),
    )


class PartnerOffer(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "partner_offers"

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partners.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    discount_code: Mapped[str | None] = mapped_column(String(60))
    destination_url: Mapped[str] = mapped_column(String(500), nullable=False)
    terms: Mapped[str] = mapped_column(Text, default="", nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    erid: Mapped[str | None] = mapped_column(String(120))
    ad_label: Mapped[str | None] = mapped_column(String(60))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category in ('food','stores','vet','grooming','services')", name="category_valid"
        ),
        CheckConstraint("status in ('draft','active','paused','archived')", name="status_valid"),
        Index("ix_partner_offers_active", "status", "category", "ends_at"),
    )


class PartnerClick(Base, UUIDPrimaryKey):
    __tablename__ = "partner_clicks"

    offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner_offers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    ua_hash: Mapped[str | None] = mapped_column(String(64))
    attribution_token: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PartnerConversion(Base, UUIDPrimaryKey):
    __tablename__ = "partner_conversions"

    offer_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner_offers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    click_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("partner_clicks.id", ondelete="SET NULL")
    )
    amount_kopecks: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PartnerInquiry(Base, UUIDPrimaryKey):
    __tablename__ = "partner_inquiries"

    company: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    phone_encrypted: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="new", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
