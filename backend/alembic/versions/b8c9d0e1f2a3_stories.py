"""stories

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-11-25 15:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("reactions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmarks_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stories")),
        sa.UniqueConstraint("public_id", name=op.f("uq_stories_public_id")),
    )
    op.create_index("ix_stories_author_id", "stories", ["author_id"])
    op.create_index("ix_stories_status", "stories", ["status"])
    op.create_index("ix_stories_status_published", "stories", ["status", "published_at"])

    op.create_table(
        "story_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_comments")),
    )
    op.create_index("ix_story_comments_story_id", "story_comments", ["story_id"])
    op.create_index("ix_story_comments_author_id", "story_comments", ["author_id"])
    op.create_index("ix_story_comments_story_created", "story_comments", ["story_id", "created_at"])

    op.create_table(
        "story_reactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reaction", sa.String(length=24), nullable=False, server_default="like"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_reactions")),
        sa.UniqueConstraint("story_id", "user_id", name="uq_story_reactions_story_user"),
    )
    op.create_index("ix_story_reactions_story_id", "story_reactions", ["story_id"])
    op.create_index("ix_story_reactions_user_id", "story_reactions", ["user_id"])

    op.create_table(
        "story_bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_bookmarks")),
        sa.UniqueConstraint("story_id", "user_id", name="uq_story_bookmarks_story_user"),
    )
    op.create_index("ix_story_bookmarks_story_id", "story_bookmarks", ["story_id"])
    op.create_index("ix_story_bookmarks_user_id", "story_bookmarks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_story_bookmarks_user_id", table_name="story_bookmarks")
    op.drop_index("ix_story_bookmarks_story_id", table_name="story_bookmarks")
    op.drop_table("story_bookmarks")
    op.drop_index("ix_story_reactions_user_id", table_name="story_reactions")
    op.drop_index("ix_story_reactions_story_id", table_name="story_reactions")
    op.drop_table("story_reactions")
    op.drop_index("ix_story_comments_story_created", table_name="story_comments")
    op.drop_index("ix_story_comments_author_id", table_name="story_comments")
    op.drop_index("ix_story_comments_story_id", table_name="story_comments")
    op.drop_table("story_comments")
    op.drop_index("ix_stories_status_published", table_name="stories")
    op.drop_index("ix_stories_status", table_name="stories")
    op.drop_index("ix_stories_author_id", table_name="stories")
    op.drop_table("stories")
