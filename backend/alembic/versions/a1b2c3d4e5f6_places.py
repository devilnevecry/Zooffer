"""places

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-11-24 18:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("moderation_reason", sa.String(length=400), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["moderated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_places")),
        sa.UniqueConstraint("public_id", name=op.f("uq_places_public_id")),
        sa.CheckConstraint(
            "category in ('vet_clinic','groomer','park','cafe','dangerous','shelter','other')",
            name="place_category_valid",
        ),
        sa.CheckConstraint(
            "status in ('pending','approved','rejected')", name="place_status_valid"
        ),
    )
    op.create_index("ix_places_reporter_id", "places", ["reporter_id"])
    op.create_index("ix_places_status", "places", ["status"])
    op.create_index("ix_places_category", "places", ["category"])
    op.create_index("ix_places_status_geo", "places", ["status", "latitude", "longitude"])
    op.create_index("ix_places_category_status", "places", ["category", "status"])


def downgrade() -> None:
    op.drop_index("ix_places_category_status", table_name="places")
    op.drop_index("ix_places_status_geo", table_name="places")
    op.drop_index("ix_places_category", table_name="places")
    op.drop_index("ix_places_status", table_name="places")
    op.drop_index("ix_places_reporter_id", table_name="places")
    op.drop_table("places")
