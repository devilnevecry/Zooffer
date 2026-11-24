"""one subscription per user

A user always has a single subscription row. Upgrades reuse it and convert the
unused time of the old plan into a price credit; they never create a second
subscription.

Revision ID: e7c1b4a9d260
Revises: d4e9f1a2b3c4
Create Date: 2026-11-24 12:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "e7c1b4a9d260"
down_revision: str | None = "d4e9f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep the newest row per user; close any historical duplicates.
    op.execute(
        """
        WITH ranked AS (
            SELECT id, row_number() OVER (
                PARTITION BY user_id ORDER BY created_at DESC, id DESC
            ) AS rn
            FROM subscriptions
        )
        UPDATE subscriptions
        SET status = 'canceled', current_period_end = now(), canceled_at = now()
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.create_index("uq_subscriptions_user", "subscriptions", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_subscriptions_user", table_name="subscriptions")
