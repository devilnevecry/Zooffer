"""animal co-owners

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-25 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "animal_co_owners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("animal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="co_owner"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["animal_id"], ["animals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_animal_co_owners")),
        sa.UniqueConstraint("animal_id", "user_id", name="uq_animal_co_owners_animal_user"),
    )
    op.create_index("ix_animal_co_owners_animal_id", "animal_co_owners", ["animal_id"])
    op.create_index("ix_animal_co_owners_user_id", "animal_co_owners", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_animal_co_owners_user_id", table_name="animal_co_owners")
    op.drop_index("ix_animal_co_owners_animal_id", table_name="animal_co_owners")
    op.drop_table("animal_co_owners")
