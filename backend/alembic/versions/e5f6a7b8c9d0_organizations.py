"""organizations

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-25 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_type", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("public_id", name=op.f("uq_organizations_public_id")),
    )
    op.create_index("ix_organizations_owner_id", "organizations", ["owner_id"])
    op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_index("ix_organizations_type", "organizations", ["org_type"])
    op.create_index("ix_organizations_status_city", "organizations", ["status", "city_id"])
    op.create_index("ix_organizations_type_status", "organizations", ["org_type", "status"])


def downgrade() -> None:
    op.drop_index("ix_organizations_type_status", table_name="organizations")
    op.drop_index("ix_organizations_status_city", table_name="organizations")
    op.drop_index("ix_organizations_type", table_name="organizations")
    op.drop_index("ix_organizations_status", table_name="organizations")
    op.drop_index("ix_organizations_owner_id", table_name="organizations")
    op.drop_table("organizations")
