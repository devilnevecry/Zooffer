"""lost reports

Revision ID: f1a2b3c4d5e6
Revises: e7c1b4a9d260
Create Date: 2026-11-24 17:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e7c1b4a9d260"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lost_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("animal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="searching"),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("last_seen_longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("last_seen_description", sa.String(length=400), nullable=True),
        sa.Column("radius_km", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("found_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lost_reports")),
        sa.UniqueConstraint("public_id", name=op.f("uq_lost_reports_public_id")),
        sa.CheckConstraint(
            "status in ('searching','found','closed')", name="lost_report_status_valid"
        ),
        sa.CheckConstraint("radius_km >= 1 and radius_km <= 100", name="lost_report_radius_valid"),
    )
    op.create_index("ix_lost_reports_reporter_id", "lost_reports", ["reporter_id"])
    op.create_index("ix_lost_reports_animal_id", "lost_reports", ["animal_id"])
    op.create_index("ix_lost_reports_status", "lost_reports", ["status"])
    op.create_index(
        "ix_lost_reports_status_geo",
        "lost_reports",
        ["status", "last_seen_latitude", "last_seen_longitude"],
    )

    op.create_table(
        "lost_sightings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("notes", sa.String(length=400), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["report_id"], ["lost_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lost_sightings")),
        sa.UniqueConstraint(
            "report_id",
            "reporter_id",
            "request_id",
            name="uq_lost_sightings_report_reporter_request",
        ),
    )
    op.create_index("ix_lost_sightings_report_id", "lost_sightings", ["report_id"])
    op.create_index("ix_lost_sightings_reporter_id", "lost_sightings", ["reporter_id"])


def downgrade() -> None:
    op.drop_index("ix_lost_sightings_reporter_id", table_name="lost_sightings")
    op.drop_index("ix_lost_sightings_report_id", table_name="lost_sightings")
    op.drop_table("lost_sightings")
    op.drop_index("ix_lost_reports_status_geo", table_name="lost_reports")
    op.drop_index("ix_lost_reports_status", table_name="lost_reports")
    op.drop_index("ix_lost_reports_animal_id", table_name="lost_reports")
    op.drop_index("ix_lost_reports_reporter_id", table_name="lost_reports")
    op.drop_table("lost_reports")
