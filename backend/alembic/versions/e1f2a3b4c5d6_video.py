"""video posts

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-11-25 18:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("media_key", sa.String(length=500), nullable=False),
        sa.Column("thumb_key", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="processing"),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_video_posts")),
        sa.UniqueConstraint("public_id", name=op.f("uq_video_posts_public_id")),
    )
    op.create_index("ix_video_posts_author_id", "video_posts", ["author_id"])
    op.create_index("ix_video_posts_status", "video_posts", ["status"])
    op.create_index("ix_video_posts_status_created", "video_posts", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_video_posts_status_created", table_name="video_posts")
    op.drop_index("ix_video_posts_status", table_name="video_posts")
    op.drop_index("ix_video_posts_author_id", table_name="video_posts")
    op.drop_table("video_posts")
