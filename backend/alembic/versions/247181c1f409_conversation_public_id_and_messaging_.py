"""conversation public id

Revision ID: 247181c1f409
Revises: c1ec09fb116c
Create Date: 2026-10-22 14:16:43.264317
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "247181c1f409"
down_revision: str | None = "c1ec09fb116c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("public_id", sa.Uuid(), nullable=True))
    op.execute("UPDATE conversations SET public_id = gen_random_uuid() WHERE public_id IS NULL")
    op.alter_column("conversations", "public_id", nullable=False)
    op.create_index(
        op.f("ix_conversations_public_id"),
        "conversations",
        ["public_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_public_id"), table_name="conversations")
    op.drop_column("conversations", "public_id")
