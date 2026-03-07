"""Add triggered_at and last_value columns to alerts

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-07 00:01:00.000000

Supports the alert engine — records when an alert last fired and
the market value that triggered it.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE alerts
            ADD COLUMN IF NOT EXISTS triggered_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS last_value   NUMERIC(12,4),
            ADD COLUMN IF NOT EXISTS trigger_count INTEGER DEFAULT 0
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS triggered_at")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS last_value")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS trigger_count")
