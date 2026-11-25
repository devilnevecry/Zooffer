"""channels

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-25 16:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channels")),
        sa.UniqueConstraint("public_id", name=op.f("uq_channels_public_id")),
    )
    op.create_index("ix_channels_owner_id", "channels", ["owner_id"])
    op.create_index("ix_channels_status", "channels", ["status"])
    op.create_index("ix_channels_status_created", "channels", ["status", "created_at"])

    op.create_table(
        "channel_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channel_subscriptions")),
        sa.UniqueConstraint("channel_id", "user_id", name="uq_channel_subscriptions_channel_user"),
    )
    op.create_index("ix_channel_subscriptions_channel_id", "channel_subscriptions", ["channel_id"])
    op.create_index("ix_channel_subscriptions_user_id", "channel_subscriptions", ["user_id"])

    op.create_table(
        "channel_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channel_posts")),
    )
    op.create_index("ix_channel_posts_channel_id", "channel_posts", ["channel_id"])
    op.create_index("ix_channel_posts_author_id", "channel_posts", ["author_id"])
    op.create_index(
        "ix_channel_posts_channel_created", "channel_posts", ["channel_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_channel_posts_channel_created", table_name="channel_posts")
    op.drop_index("ix_channel_posts_author_id", table_name="channel_posts")
    op.drop_index("ix_channel_posts_channel_id", table_name="channel_posts")
    op.drop_table("channel_posts")
    op.drop_index("ix_channel_subscriptions_user_id", table_name="channel_subscriptions")
    op.drop_index("ix_channel_subscriptions_channel_id", table_name="channel_subscriptions")
    op.drop_table("channel_subscriptions")
    op.drop_index("ix_channels_status_created", table_name="channels")
    op.drop_index("ix_channels_status", table_name="channels")
    op.drop_index("ix_channels_owner_id", table_name="channels")
    op.drop_table("channels")
