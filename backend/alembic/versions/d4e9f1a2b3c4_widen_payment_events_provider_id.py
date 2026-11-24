"""widen payment events provider id

Telegram Stars charge ids are long; ``telegram_stars:<charge_id>`` exceeds the
old 120-character column and made successful_payment activation fail.

Revision ID: d4e9f1a2b3c4
Revises: b41c7d90a2e5
Create Date: 2026-11-24 12:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e9f1a2b3c4"
down_revision: str | None = "b41c7d90a2e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "payment_events",
        "provider_event_id",
        existing_type=sa.String(length=120),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "payment_events",
        "provider_event_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
