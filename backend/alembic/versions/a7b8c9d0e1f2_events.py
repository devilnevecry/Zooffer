"""events

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-25 14:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
        sa.UniqueConstraint("public_id", name=op.f("uq_events_public_id")),
    )
    op.create_index("ix_events_organizer_id", "events", ["organizer_id"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_type", "events", ["event_type"])
    op.create_index("ix_events_starts_at", "events", ["starts_at"])
    op.create_index("ix_events_status_starts", "events", ["status", "starts_at"])

    op.create_table(
        "event_attendees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="going"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_attendees")),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_attendees_event_user"),
    )
    op.create_index("ix_event_attendees_event_id", "event_attendees", ["event_id"])
    op.create_index("ix_event_attendees_user_id", "event_attendees", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_event_attendees_user_id", table_name="event_attendees")
    op.drop_index("ix_event_attendees_event_id", table_name="event_attendees")
    op.drop_table("event_attendees")
    op.drop_index("ix_events_status_starts", table_name="events")
    op.drop_index("ix_events_starts_at", table_name="events")
    op.drop_index("ix_events_type", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_organizer_id", table_name="events")
    op.drop_table("events")
