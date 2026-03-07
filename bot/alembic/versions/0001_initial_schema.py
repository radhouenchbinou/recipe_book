"""Initial schema — baseline from infra/postgres/schema.sql

Revision ID: 0001
Revises:
Create Date: 2026-03-07 00:00:00.000000

This migration establishes the baseline schema that was previously
managed by infra/postgres/schema.sql.  Future schema changes should
be added as incremental revisions on top of this baseline.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── symbols ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            id         SERIAL PRIMARY KEY,
            ticker     VARCHAR(10) NOT NULL UNIQUE,
            name       VARCHAR(255),
            asset_type VARCHAR(20) DEFAULT 'stock',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── market_data ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id          SERIAL PRIMARY KEY,
            symbol_id   INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
            trade_date  TIMESTAMPTZ NOT NULL,
            open_price  NUMERIC(12,4),
            high_price  NUMERIC(12,4),
            low_price   NUMERIC(12,4),
            close_price NUMERIC(12,4) NOT NULL,
            volume      BIGINT,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (symbol_id, trade_date)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date ON market_data (symbol_id, trade_date DESC)")

    # ── news_items ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
            id           SERIAL PRIMARY KEY,
            headline     TEXT NOT NULL,
            source       VARCHAR(100),
            url          TEXT,
            published_at TIMESTAMPTZ,
            fetched_at   TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (url)
        )
    """)

    # ── news_symbols ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS news_symbols (
            news_id   INTEGER REFERENCES news_items(id) ON DELETE CASCADE,
            symbol_id INTEGER REFERENCES symbols(id)   ON DELETE CASCADE,
            PRIMARY KEY (news_id, symbol_id)
        )
    """)

    # ── analysis_scores ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS analysis_scores (
            id               SERIAL PRIMARY KEY,
            symbol_id        INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
            technical_score  NUMERIC(5,2),
            sentiment_score  NUMERIC(5,2),
            geo_risk_score   NUMERIC(5,2),
            composite_score  NUMERIC(5,2),
            scored_at        TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_analysis_scores_symbol_date ON analysis_scores (symbol_id, scored_at DESC)")

    # ── recommendations ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id               SERIAL PRIMARY KEY,
            symbol_id        INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
            analysis_score_id INTEGER REFERENCES analysis_scores(id),
            action           VARCHAR(10) NOT NULL CHECK (action IN ('buy','sell','hold')),
            confidence       NUMERIC(4,3),
            position_size    NUMERIC(4,3),
            rationale        TEXT,
            source           VARCHAR(20) DEFAULT 'claude',
            raw_response     TEXT,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_symbol_date ON recommendations (symbol_id, created_at DESC)")

    # ── claude_usage ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS claude_usage (
            id            SERIAL PRIMARY KEY,
            symbol_id     INTEGER REFERENCES symbols(id),
            input_tokens  INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            trigger_reason VARCHAR(50),
            called_at     TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── alerts ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(100) NOT NULL,
            symbol_id  INTEGER REFERENCES symbols(id) ON DELETE CASCADE,
            condition  VARCHAR(20) NOT NULL,
            threshold  NUMERIC(12,4) NOT NULL,
            active     BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── seed symbols ──────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO symbols (ticker, name, asset_type) VALUES
            ('SPY',  'SPDR S&P 500 ETF',          'etf'),
            ('QQQ',  'Invesco QQQ Trust',          'etf'),
            ('GLD',  'SPDR Gold Shares',           'etf'),
            ('AAPL', 'Apple Inc.',                 'stock'),
            ('MSFT', 'Microsoft Corporation',      'stock'),
            ('NVDA', 'NVIDIA Corporation',         'stock')
        ON CONFLICT (ticker) DO NOTHING
    """)


def downgrade() -> None:
    for table in ["alerts", "claude_usage", "recommendations",
                  "analysis_scores", "news_symbols", "news_items",
                  "market_data", "symbols"]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
