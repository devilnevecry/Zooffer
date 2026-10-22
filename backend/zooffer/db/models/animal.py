from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Animal(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "animals"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    species: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    breed_id: Mapped[int | None] = mapped_column(ForeignKey("breeds.id", ondelete="SET NULL"))
    breed_text: Mapped[str | None] = mapped_column(String(120))
    sex: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    colour: Mapped[str | None] = mapped_column(String(80))
    size: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    has_pedigree: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pedigree_registry: Mapped[str | None] = mapped_column(String(40))
    pedigree_number: Mapped[str | None] = mapped_column(String(80))
    vaccinated: Mapped[bool | None] = mapped_column(Boolean)
    health_notes: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("sex in ('male','female','unknown')", name="sex_valid"),
        CheckConstraint(
            "species in ('dog','cat','bird','rodent','reptile','other')", name="species_valid"
        ),
        Index("ix_animals_owner_archived", "owner_id", "archived_at"),
    )


class AnimalPhoto(Base, UUIDPrimaryKey):
    __tablename__ = "animal_photos"

    animal_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(200))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("animal_id", "position", name="uq_animal_photos_position"),)


class AnimalDocument(Base, UUIDPrimaryKey):
    """Private document (pedigree papers). Never public; served via signed, authorised URLs."""

    __tablename__ = "animal_documents"

    animal_id: Mapped[UUID] = mapped_column(
        ForeignKey("animals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), default="pedigree", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="private", nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
