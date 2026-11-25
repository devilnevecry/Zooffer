from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Story(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "stories"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    reactions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bookmarks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (Index("ix_stories_status_published", "status", "published_at"),)


class StoryComment(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "story_comments"

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("ix_story_comments_story_created", "story_id", "created_at"),)


class StoryReaction(Base, UUIDPrimaryKey):
    __tablename__ = "story_reactions"

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reaction: Mapped[str] = mapped_column(String(24), default="like", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("story_id", "user_id", name="uq_story_reactions_story_user"),
    )


class StoryBookmark(Base, UUIDPrimaryKey):
    __tablename__ = "story_bookmarks"

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("story_id", "user_id", name="uq_story_bookmarks_story_user"),
    )
