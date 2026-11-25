from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class VideoPost(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "video_posts"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    media_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumb_key: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(16), default="processing", index=True, nullable=False
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (Index("ix_video_posts_status_created", "status", "created_at"),)
