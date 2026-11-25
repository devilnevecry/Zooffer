from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from zooffer.db.base import Base, Timestamps, UUIDPrimaryKey


class Question(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "questions"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True, nullable=False)
    best_answer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("answers.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (Index("ix_questions_status_created", "status", "created_at"),)


class Answer(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "answers"

    public_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_best: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vet_marked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (Index("ix_answers_question_created", "question_id", "created_at"),)
