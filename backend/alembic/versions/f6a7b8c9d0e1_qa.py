"""qa community

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-25 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("best_answer_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
        sa.UniqueConstraint("public_id", name=op.f("uq_questions_public_id")),
    )
    op.create_index("ix_questions_author_id", "questions", ["author_id"])
    op.create_index("ix_questions_status", "questions", ["status"])
    op.create_index("ix_questions_status_created", "questions", ["status", "created_at"])

    op.create_table(
        "answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_best", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("vet_marked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers")),
        sa.UniqueConstraint("public_id", name=op.f("uq_answers_public_id")),
    )
    op.create_index("ix_answers_question_id", "answers", ["question_id"])
    op.create_index("ix_answers_author_id", "answers", ["author_id"])
    op.create_index("ix_answers_question_created", "answers", ["question_id", "created_at"])

    op.create_foreign_key(
        "fk_questions_best_answer_id_answers",
        "questions",
        "answers",
        ["best_answer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_questions_best_answer_id_answers", "questions", type_="foreignkey")
    op.drop_index("ix_answers_question_created", table_name="answers")
    op.drop_index("ix_answers_author_id", table_name="answers")
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_questions_status_created", table_name="questions")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_index("ix_questions_author_id", table_name="questions")
    op.drop_table("questions")
