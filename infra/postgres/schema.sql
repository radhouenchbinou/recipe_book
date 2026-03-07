-- Trading Bot Database Schema
-- Sprint 1 — Task S1-T1-002

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────
-- 1. Symbols: tracked instruments
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS symbols (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker      VARCHAR(10) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    asset_type  VARCHAR(20) NOT NULL CHECK (asset_type IN ('stock', 'etf', 'gold', 'crypto')),
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 2. Market data: daily OHLCV snapshots
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_data (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id   UUID NOT NULL REFERENCES symbols(id),
    trade_date  DATE NOT NULL,
    open        NUMERIC(12, 4) NOT NULL,
    high        NUMERIC(12, 4) NOT NULL,
    low         NUMERIC(12, 4) NOT NULL,
    close       NUMERIC(12, 4) NOT NULL,
    volume      BIGINT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol_id, trade_date)
);

CREATE INDEX idx_market_data_symbol_date ON market_data (symbol_id, trade_date DESC);

-- ─────────────────────────────────────────
-- 3. News items
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_items (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    headline     TEXT NOT NULL,
    summary      TEXT,
    source       VARCHAR(100),
    url          TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json     JSONB
);

CREATE INDEX idx_news_published ON news_items (published_at DESC);

-- ─────────────────────────────────────────
-- 4. News → Symbol associations
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_symbols (
    news_id   UUID NOT NULL REFERENCES news_items(id) ON DELETE CASCADE,
    symbol_id UUID NOT NULL REFERENCES symbols(id),
    PRIMARY KEY (news_id, symbol_id)
);

-- ─────────────────────────────────────────
-- 5. Analysis scores
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis_scores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id           UUID NOT NULL REFERENCES symbols(id),
    scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    technical_score     NUMERIC(5, 2),   -- RSI-/MACD-based, 0–100
    sentiment_score     NUMERIC(5, 4),   -- -1.0 to +1.0
    geo_risk_score      NUMERIC(5, 2),   -- 0–100 (higher = riskier)
    composite_score     NUMERIC(5, 2),   -- weighted aggregate, 0–100
    indicator_snapshot  JSONB            -- raw indicator values
);

CREATE INDEX idx_scores_symbol_time ON analysis_scores (symbol_id, scored_at DESC);

-- ─────────────────────────────────────────
-- 6. Claude recommendations
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id       UUID NOT NULL REFERENCES symbols(id),
    score_id        UUID REFERENCES analysis_scores(id),
    recommended_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action          VARCHAR(10) NOT NULL CHECK (action IN ('buy', 'sell', 'hold')),
    confidence      NUMERIC(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    reasoning       TEXT,
    source          VARCHAR(20) NOT NULL DEFAULT 'claude' CHECK (source IN ('claude', 'fallback')),
    raw_response    JSONB
);

CREATE INDEX idx_recs_symbol_time ON recommendations (symbol_id, recommended_at DESC);

-- ─────────────────────────────────────────
-- 7. Claude API usage tracking
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS claude_usage (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    called_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usage_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    input_tokens    INT NOT NULL DEFAULT 0,
    output_tokens   INT NOT NULL DEFAULT 0,
    symbol_id       UUID REFERENCES symbols(id),
    trigger_reason  VARCHAR(100)
);

CREATE INDEX idx_claude_usage_date ON claude_usage (usage_date DESC);

-- ─────────────────────────────────────────
-- 8. Alerts
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol_id       UUID NOT NULL REFERENCES symbols(id),
    alert_type      VARCHAR(30) NOT NULL CHECK (alert_type IN ('price_above', 'price_below', 'score_above', 'score_below', 'recommendation')),
    threshold       NUMERIC(12, 4),
    message         TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    triggered_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 9. Order ledger (Phase 3 Sprint 2)
--    Audit trail for every broker order.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_ledger (
    id                SERIAL PRIMARY KEY,
    order_id          VARCHAR(100)  NOT NULL,
    broker            VARCHAR(50)   NOT NULL DEFAULT 'alpaca-paper',
    symbol            VARCHAR(20)   NOT NULL,
    side              VARCHAR(4)    NOT NULL CHECK (side IN ('buy', 'sell')),
    qty               INTEGER       NOT NULL CHECK (qty > 0),
    status            VARCHAR(20)   NOT NULL,
    filled_price      NUMERIC(12, 4),
    error             TEXT,
    source            VARCHAR(50),
    recommendation_id INTEGER,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_ledger_symbol      ON order_ledger (symbol);
CREATE INDEX IF NOT EXISTS idx_order_ledger_created_at  ON order_ledger (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_ledger_broker_status ON order_ledger (broker, status);

-- ─────────────────────────────────────────
-- Seed: default tracked symbols
-- ─────────────────────────────────────────
INSERT INTO symbols (ticker, name, asset_type) VALUES
    ('SPY',  'SPDR S&P 500 ETF Trust',            'etf'),
    ('QQQ',  'Invesco QQQ Trust',                  'etf'),
    ('GLD',  'SPDR Gold Shares',                   'gold'),
    ('AAPL', 'Apple Inc.',                          'stock'),
    ('MSFT', 'Microsoft Corporation',               'stock'),
    ('NVDA', 'NVIDIA Corporation',                  'stock')
ON CONFLICT (ticker) DO NOTHING;
