"""Add order_ledger table for trade audit trail

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-07 00:04:00.000000

Records every order submitted through the broker layer (paper or live).
Enables reporting, audit, P&L reconciliation, and duplicate-detection.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS order_ledger (
            id              SERIAL PRIMARY KEY,
            order_id        VARCHAR(100)   NOT NULL,
            broker          VARCHAR(50)    NOT NULL DEFAULT 'alpaca-paper',
            symbol          VARCHAR(20)    NOT NULL,
            side            VARCHAR(4)     NOT NULL CHECK (side IN ('buy', 'sell')),
            qty             INTEGER        NOT NULL CHECK (qty > 0),
            status          VARCHAR(20)    NOT NULL,
            filled_price    NUMERIC(12, 4),
            error           TEXT,
            source          VARCHAR(50),   -- 'rebalance' | 'stop_loss' | 'manual'
            recommendation_id INTEGER REFERENCES recommendations(id) ON DELETE SET NULL,
            created_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_ledger_symbol
            ON order_ledger (symbol)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_ledger_created_at
            ON order_ledger (created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_ledger_broker_status
            ON order_ledger (broker, status)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_order_ledger_broker_status")
    op.execute("DROP INDEX IF EXISTS idx_order_ledger_created_at")
    op.execute("DROP INDEX IF EXISTS idx_order_ledger_symbol")
    op.execute("DROP TABLE IF EXISTS order_ledger")
