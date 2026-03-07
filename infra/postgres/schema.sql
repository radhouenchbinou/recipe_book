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
-- 9. Users (multi-user auth)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          VARCHAR(16) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'trader', 'viewer')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 10. Refresh tokens (one per active session)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,   -- SHA-256 of the raw token
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id);

-- ─────────────────────────────────────────
-- 11. User settings (notification prefs)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_settings (
    user_id         INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    notify_slack    BOOLEAN NOT NULL DEFAULT FALSE,
    notify_email    BOOLEAN NOT NULL DEFAULT FALSE,
    notify_sms      BOOLEAN NOT NULL DEFAULT FALSE,
    slack_webhook   TEXT,
    email_addr      TEXT,
    phone_number    TEXT,
    risk_tolerance  VARCHAR(8) NOT NULL DEFAULT 'medium' CHECK (risk_tolerance IN ('low', 'medium', 'high')),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- 12. Bot runs (scheduler cycle audit log)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_runs (
    id               SERIAL PRIMARY KEY,
    run_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status           VARCHAR(16) NOT NULL CHECK (status IN ('ok', 'partial', 'error')),
    symbols_scanned  INT NOT NULL DEFAULT 0,
    recs_generated   INT NOT NULL DEFAULT 0,
    claude_calls     INT NOT NULL DEFAULT 0,
    duration_ms      INT,
    error_msg        TEXT
);

CREATE INDEX idx_bot_runs_run_at ON bot_runs (run_at DESC);

-- ─────────────────────────────────────────
-- 13. Position history (daily P&L snapshots)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS position_history (
    id              SERIAL PRIMARY KEY,
    symbol_id       UUID NOT NULL REFERENCES symbols(id),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    qty             NUMERIC(15, 6) NOT NULL,
    avg_entry       NUMERIC(12, 4) NOT NULL,
    market_val      NUMERIC(15, 4) NOT NULL,
    unrealised_pnl  NUMERIC(15, 4) NOT NULL
);

CREATE INDEX idx_position_history_symbol ON position_history (symbol_id, recorded_at DESC);

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
