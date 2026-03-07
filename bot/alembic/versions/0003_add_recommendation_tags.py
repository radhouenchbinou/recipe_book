"""Add tags and portfolio_context columns to recommendations

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-07 00:02:00.000000

Supports advanced Claude prompt strategies — stores the portfolio
context digest used when building the prompt, and freeform tags
for filtering (e.g. 'earnings', 'macro', 'geopolitical').
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE recommendations
            ADD COLUMN IF NOT EXISTS tags              TEXT[],
            ADD COLUMN IF NOT EXISTS portfolio_context JSONB,
            ADD COLUMN IF NOT EXISTS model_version     VARCHAR(50)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_recommendations_tags
            ON recommendations USING gin(tags)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_recommendations_tags")
    op.execute("ALTER TABLE recommendations DROP COLUMN IF EXISTS tags")
    op.execute("ALTER TABLE recommendations DROP COLUMN IF EXISTS portfolio_context")
    op.execute("ALTER TABLE recommendations DROP COLUMN IF EXISTS model_version")
