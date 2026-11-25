"""services

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-25 11:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("price_from_kopecks", sa.Integer(), nullable=True),
        sa.Column("formats", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=True),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_profiles")),
        sa.UniqueConstraint("public_id", name=op.f("uq_service_profiles_public_id")),
        sa.UniqueConstraint("user_id", "category", name="uq_service_profiles_user_category"),
    )
    op.create_index("ix_service_profiles_user_id", "service_profiles", ["user_id"])
    op.create_index("ix_service_profiles_status", "service_profiles", ["status"])
    op.create_index("ix_service_profiles_category", "service_profiles", ["category"])
    op.create_index("ix_service_profiles_status_city", "service_profiles", ["status", "city_id"])
    op.create_index(
        "ix_service_profiles_category_status", "service_profiles", ["category", "status"]
    )

    op.create_table(
        "service_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_ref", sa.String(length=80), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
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
        sa.ForeignKeyConstraint(["profile_id"], ["service_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_reviews")),
        sa.UniqueConstraint("profile_id", "author_id", name="uq_service_reviews_profile_author"),
    )
    op.create_index("ix_service_reviews_profile_id", "service_reviews", ["profile_id"])
    op.create_index("ix_service_reviews_author_id", "service_reviews", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_service_reviews_author_id", table_name="service_reviews")
    op.drop_index("ix_service_reviews_profile_id", table_name="service_reviews")
    op.drop_table("service_reviews")
    op.drop_index("ix_service_profiles_category_status", table_name="service_profiles")
    op.drop_index("ix_service_profiles_status_city", table_name="service_profiles")
    op.drop_index("ix_service_profiles_category", table_name="service_profiles")
    op.drop_index("ix_service_profiles_status", table_name="service_profiles")
    op.drop_index("ix_service_profiles_user_id", table_name="service_profiles")
    op.drop_table("service_profiles")
