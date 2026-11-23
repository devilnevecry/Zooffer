"""partner inquiry telegram contact

Revision ID: b41c7d90a2e5
Revises: 247181c1f409
Create Date: 2026-11-23 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b41c7d90a2e5"
down_revision: str | None = "247181c1f409"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("partner_inquiries", sa.Column("telegram_encrypted", sa.Text(), nullable=True))
    op.alter_column("partner_inquiries", "email_encrypted", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE partner_inquiries SET email_encrypted = '' WHERE email_encrypted IS NULL")
    op.alter_column("partner_inquiries", "email_encrypted", existing_type=sa.Text(), nullable=False)
    op.drop_column("partner_inquiries", "telegram_encrypted")
