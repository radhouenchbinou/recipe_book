# CLAUDE.md — Trading Bot Project Work Contract

This file defines how Claude Code operates on this repository.
Every session **must** follow these rules without exception.

---

## Project Identity

**Name:** AI-Powered Trading Bot
**Phase:** 2 of 3 — **Sprint 2 COMPLETE ✅ — Live Executor · Equity Chart API · Performance + Backtest Dashboard**
**Goal:** Automated stock/ETF/gold trading with Claude API recommendations, sentiment analysis, and geopolitical risk scoring.

### Active Branch Convention
All development branches follow: `claude/<description>-HUmPC`

| Sprint | Branch | Status |
|--------|--------|--------|
| P1-S1 | `claude/trading-bot-project-planning-HUmPC` | ✅ Merged to main |
| P1-S2 | `claude/trading-bot-sprint2-analysis-engine-HUmPC` | ✅ Merged to main |
| P1-S3 | `claude/trading-bot-sprint3-claude-integration-HUmPC` | ✅ Merged to main |
| P1-S4 | `claude/trading-bot-sprint4-api-dashboard-HUmPC` | ✅ Merged to main |
| P1-S5 | `claude/trading-bot-sprint5-production-HUmPC` | ✅ Merged to main |
| P2-S1 | `claude/trading-bot-phase2-sprint1-HUmPC` | ✅ Merged to main |
| P2-S2 | `claude/trading-bot-phase2-sprint2-HUmPC` | ✅ Complete — pending merge |

---

## Repository Structure

```
.
├── CLAUDE.md                    ← this file (work contract)
├── agent.py                     ← PM agent CLI
├── config.py                    ← agent config
├── prompts.py                   ← agent prompts
├── requirements.txt             ← PM agent Python deps
│
├── api/                         ← Node.js 20 Express REST API
│   ├── src/
│   │   ├── app.js               ← entry point, all routes registered
│   │   ├── middleware/
│   │   │   ├── auth.js          ← JWT requireAuth + signToken
│   │   │   ├── logger.js        ← structured JSON request logger
│   │   │   └── errorHandler.js  ← { data, error, meta } envelope
│   │   ├── routes/
│   │   │   ├── health.js        ← GET /health (postgres + redis checks)
│   │   │   ├── auth.js          ← POST /auth/login → JWT
│   │   │   ├── portfolio.js     ← GET /api/v1/portfolio + /positions
│   │   │   ├── recommendations.js ← GET /api/v1/recommendations[/:symbol]
│   │   │   ├── marketData.js    ← GET /api/v1/market-data/:symbol
│   │   │   ├── alerts.js        ← CRUD /api/v1/alerts
│   │   │   └── v2/              ← Phase 2 endpoints
│   │   │       ├── backtest.js  ← GET /api/v2/backtest[/:symbol]
│   │   │       ├── performance.js ← GET /api/v2/performance[/:symbol]
│   │   │       ├── rebalance.js ← GET /api/v2/rebalance · POST /api/v2/rebalance/execute
│   │   │       └── equity.js    ← GET /api/v2/equity[/:symbol]?days=N (equity time-series)
│   │   └── services/
│   │       ├── db.js            ← pg connection pool
│   │       └── redis.js         ← ioredis + cached() helper
│   ├── tests/                   ← Jest + supertest API tests
│   ├── package.json
│   └── Dockerfile
│
├── bot/                         ← Python 3.11 trading bot engine
│   ├── main.py                  ← entry point
│   ├── config.py                ← env-var config
│   ├── db.py                    ← SQLAlchemy session factory
│   ├── collectors/
│   │   ├── market_data.py       ← Yahoo Finance OHLCV (S1-T2-001)
│   │   └── news_fetcher.py      ← RSS news + symbol tagging (S1-T2-002)
│   ├── broker/
│   │   └── connector.py         ← Alpaca paper trading (S1-T3-001)
│   ├── analysis/
│   │   ├── indicators.py        ← RSI, MACD, Bollinger, SMA/EMA (S2-T1-001)
│   │   ├── sentiment.py         ← FinBERT + lexicon fallback (S2-T2-001)
│   │   ├── geo_risk.py          ← geo event detection, 0-100 score (S2-T3-001)
│   │   └── pipeline.py          ← orchestrator → composite score → DB
│   ├── claude/
│   │   ├── usage_tracker.py     ← daily token budget enforcement
│   │   ├── prompt_builder.py    ← structured <2000-token prompts
│   │   ├── client.py            ← Anthropic SDK + retry
│   │   ├── trigger.py           ← smart trigger (delta/neutral/budget)
│   │   ├── parser.py            ← JSON response parser + DB persist
│   │   ├── fallback.py          ← rule-based recommender
│   │   └── recommender.py       ← top-level orchestrator
│   ├── scheduler/
│   │   ├── jobs.py              ← APScheduler cron jobs (4 jobs)
│   │   └── health.py            ← /health HTTP server
│   ├── backtest/                ← Phase 2: backtesting engine
│   │   └── engine.py            ← BacktestEngine (next-day open, Sharpe, drawdown, win rate)
│   ├── portfolio/               ← Phase 2: portfolio management
│   │   ├── rebalancer.py        ← score-weighted target allocation (80/20 split)
│   │   └── performance.py       ← PerformanceAnalytics (P&L, Sharpe, drawdown aggregation)
│   ├── risk/                    ← Phase 2: live trading risk guard
│   │   └── guard.py             ← RiskGuard (position limits, stop-loss, daily loss cap)
│   ├── trading/                 ← Phase 2: live order execution
│   │   └── executor.py          ← LiveTradeExecutor (risk-checked paper orders, stop-loss scan)
│   ├── tests/                   ← pytest unit tests (all modules)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
│
├── dashboard/                   ← React 18 + Vite frontend
│   ├── src/
│   │   ├── main.jsx             ← React entry, QueryClient, Router
│   │   ├── App.jsx              ← routes + ProtectedRoute
│   │   ├── index.css            ← dark theme CSS vars
│   │   ├── hooks/
│   │   │   └── useAuth.js       ← JWT login/logout state
│   │   ├── services/
│   │   │   └── api.js           ← axios client + auth interceptor
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── DashboardLayout.jsx  ← sidebar nav (6 links incl. Performance + Backtest)
│   │   │   ├── PortfolioPage.jsx    ← account stats + positions table
│   │   │   ├── RecommendationsPage.jsx ← cards + filters
│   │   │   ├── MarketPage.jsx       ← heatmap tiles + price chart
│   │   │   ├── AlertsPage.jsx       ← CRUD alert management
│   │   │   ├── PerformancePage.jsx  ← equity chart · rec stats · rebalance panel (Phase 2)
│   │   │   └── BacktestPage.jsx     ← signal history by symbol (Phase 2)
│   │   └── __tests__/           ← Vitest + Testing Library
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf               ← SPA fallback + API proxy
│   └── Dockerfile               ← multi-stage build
│
└── infra/
    ├── docker-compose.yml       ← all 5 services (postgres, redis, api, bot, dashboard)
    ├── docker-compose.prod.yml  ← production compose (GHCR images, secrets via env)
    ├── postgres/
    │   └── schema.sql           ← 8 tables + indexes + seed symbols
    ├── k6/
    │   ├── smoke-test.js        ← 1 VU, 30s — sanity check
    │   └── load-test.js         ← 100 VU ramp, p99 < 500ms thresholds
    ├── e2e/
    │   └── acceptance.test.js   ← full user journey E2E (Node test runner)
    └── monitoring/
        ├── prometheus/
        │   ├── prometheus.yml   ← scrape configs (api, bot, pg, redis)
        │   └── alerts.yml       ← 12 alert rules (down, latency, budget, disk)
        └── grafana/
            └── dashboards/
                └── trading-bot.json  ← 9-panel overview dashboard
```

---

## Sprint Status

### Phase 1 (Complete ✅)

| Sprint | Week | Focus | Status |
|--------|------|-------|--------|
| 1 | Week 1 | Docker · DB schema · Data pipeline · Broker connector | ✅ Done |
| 2 | Week 2 | Technical indicators · Sentiment · Geo risk scoring | ✅ Done |
| 3 | Week 3 | Claude API · Smart trigger · Fallback recommender | ✅ Done |
| 4 | Week 4 | REST API endpoints · React dashboard | ✅ Done |
| 5 | Week 5 | CI/CD · Load testing · Security · Monitoring · E2E tests | ✅ Done |

### Phase 2 (In Progress 🔄)

| Sprint | Focus | Status |
|--------|-------|--------|
| P2-S1 | Backtesting engine · Portfolio rebalancer · Performance analytics · Risk guard · API v2 | ✅ Done |
| P2-S2 | Live trade executor · Equity chart API · Performance + Backtest dashboard pages | ✅ Done |
| P2-S3 | Portfolio optimization · Multi-symbol rebalancing · Advanced risk metrics | ⏳ Upcoming |

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Bot Engine | Python, APScheduler, FinBERT | 3.11 |
| API Server | Node.js, Express, JWT | 20 / 4.x |
| Frontend | React, Vite, Recharts, TanStack Query | 18 / 5.x |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| Broker | Alpaca Markets API (paper only in Phase 1) | v2 |
| AI | Anthropic Claude (`claude-sonnet-4-6`) | — |
| Infra | Docker Compose (dev) | — |
| Testing (Python) | pytest, pytest-cov | — |
| Testing (Node) | Jest, supertest | — |
| Testing (React) | Vitest, Testing Library | — |

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | — | Get JWT token |
| GET | `/health` | — | Service health check |
| GET | `/api/v1/portfolio` | ✅ | Account summary (Alpaca) |
| GET | `/api/v1/portfolio/positions` | ✅ | Open positions |
| GET | `/api/v1/recommendations` | ✅ | Paginated feed (filter: symbol, source, action) |
| GET | `/api/v1/recommendations/:symbol` | ✅ | Latest for one symbol |
| GET | `/api/v1/market-data/:symbol` | ✅ | OHLCV + indicators (5-min cache) |
| GET | `/api/v1/alerts` | ✅ | List all alerts |
| POST | `/api/v1/alerts` | ✅ | Create alert |
| DELETE | `/api/v1/alerts/:id` | ✅ | Delete alert |
| PATCH | `/api/v1/alerts/:id` | ✅ | Toggle active/inactive |
| GET | `/api/v2/backtest` | ✅ | List symbols with backtest data |
| GET | `/api/v2/backtest/:symbol` | ✅ | Backtest signals for a symbol |
| GET | `/api/v2/performance` | ✅ | Portfolio-level performance aggregate |
| GET | `/api/v2/performance/:symbol` | ✅ | Per-symbol performance history |
| GET | `/api/v2/rebalance` | ✅ | Compute rebalance plan (dry run) |
| POST | `/api/v2/rebalance/execute` | ✅ | Queue rebalance execution (paper only) |
| GET | `/api/v2/equity` | ✅ | Portfolio equity time-series (days param) |
| GET | `/api/v2/equity/:symbol` | ✅ | Per-symbol equity curve for P&L chart |

All responses: `{ data, error, meta }` envelope.

---

## Environment Variables

Never hardcode secrets. All credentials go in `.env` (gitignored).

```bash
# Broker (paper only in Phase 1)
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Claude AI
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_DAILY_CALL_BUDGET=0.25     # max 25% of daily quota

# Database
DATABASE_URL=postgresql://trader:trader@localhost:5432/tradingbot

# Redis
REDIS_URL=redis://localhost:6379

# API
JWT_SECRET=...                    # change in production
API_PORT=3000

# Dashboard (dev)
DEV_USERNAME=admin
DEV_PASSWORD=changeme

# Bot scheduler (optional overrides)
MARKET_DATA_CRON="0 18 * * 1-5"
NEWS_FETCH_CRON="*/30 * * * *"
ANALYSIS_CRON="30 18 * * 1-5"
RECOMMENDATION_CRON="45 18 * * 1-5"
```

---

## Coding Standards

### Python (bot/)
- Python 3.11+; type hints required on all public functions
- `black` for formatting, `flake8` for linting
- 80%+ test coverage on every module (`pytest`)
- Docstrings on all classes and public methods
- Logging via `structlog`; **no** `print()` in production code

### Node.js (api/)
- ES Modules (`"type": "module"` in package.json)
- All routes must have input validation (`zod`)
- All endpoints must return `{ data, error, meta }` envelope
- HTTP responses: 200/201 success, 400 validation, 401 auth, 500 server error

### React (dashboard/)
- Functional components only; no class components
- `react-query` for all server state
- `useAuth` hook for all auth state

### General
- No secrets in code or git history
- Every PR must have tests
- Commit messages: `type(scope): description`
  - Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `ci`

---

## Commands

```bash
# ── Docker ─────────────────────────────────────────────────────────────────
# Start all 5 services (postgres, redis, api, bot, dashboard)
docker-compose -f infra/docker-compose.yml up

# Rebuild a single service
docker-compose -f infra/docker-compose.yml up --build api

# ── Bot ────────────────────────────────────────────────────────────────────
cd bot && python main.py                        # run bot locally
cd bot && pytest --cov=. --cov-report=term-missing  # run all bot tests

# ── API ────────────────────────────────────────────────────────────────────
cd api && npm run dev                           # run API locally (hot-reload)
cd api && npm test                              # run API tests

# ── Dashboard ──────────────────────────────────────────────────────────────
cd dashboard && npm run dev                     # run dashboard locally (:5173)
cd dashboard && npm test                        # run component tests

# ── Database ───────────────────────────────────────────────────────────────
cd bot && alembic upgrade head                  # apply migrations
cd bot && alembic downgrade -1                  # rollback one migration

# ── Load & E2E Tests ───────────────────────────────────────────────────────
# Smoke test (1 VU, 30s — quick sanity)
k6 run infra/k6/smoke-test.js -e BASE_URL=http://localhost:3000

# Load test (100 VU ramp, p99 < 500ms)
k6 run infra/k6/load-test.js \
  -e BASE_URL=http://localhost:3000 \
  -e USERNAME=admin \
  -e PASSWORD=changeme

# E2E acceptance tests (full user journey)
BASE_URL=http://localhost:3000 cd api && npm run e2e

# ── CI/CD ───────────────────────────────────────────────────────────────────
# Workflows: .github/workflows/ci.yml (on every push/PR)
#            .github/workflows/deploy.yml (on merge to main)

# ── Monitoring ──────────────────────────────────────────────────────────────
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3001 (admin / $GRAFANA_PASSWORD)

# ── PM Agent ───────────────────────────────────────────────────────────────
python agent.py                                 # interactive session
python agent.py --action plan_phase1            # generate sprint plan
python agent.py --action sprint_tasks --sprint 5
python agent.py --action status_report --week 4
python agent.py --action identify_risks
```

---

## Git Workflow

- **Branch pattern:** `claude/<description>-HUmPC`
- **Never push directly to main** — always branch → merge
- Commit after every meaningful unit of work
- Push at end of every session
- Create new branch at the start of each sprint

---

## Decision Gates

| Gate | Transition | Criteria | Status |
|------|-----------|----------|--------|
| G1 | S1 → S2 | Docker up, DB schema, data pipeline, Alpaca connected | ✅ Passed |
| G2 | S2 → S3 | All 3 score types producing values, tests green | ✅ Passed |
| G3 | S3 → S4 | Claude recommendations working, fallback tested, usage capped | ✅ Passed |
| G4 | S4 → S5 | API <200ms p99, dashboard showing live data | ✅ Passed |
| G5 | S5 → Prod | CI green, load test passed, security audit clean, E2E passing | ✅ Passed |
| G6 | P2-S1 → P2-S2 | Backtest engine, rebalancer, risk guard, API v2 tests green | ✅ Passed |
| G7 | P2-S2 → P2-S3 | Executor paper trades work, equity chart renders, dashboard tests green | ✅ Ready for review |

---

## Non-Negotiables

1. **Paper trading only** in Phase 1 — no real money API calls ever
2. **Claude usage cap** — never exceed 30% of daily quota without explicit approval
3. **Tests before merge** — no code merged without passing tests
4. **No `.env` in git** — ever
5. **Structured logging** — all services must emit JSON logs
6. **Health endpoints** — every service exposes `/health`
7. **`{ data, error, meta }` envelope** — all API responses

---

## Contacts / Roles

| Role | Responsibility |
|------|---------------|
| Claude Code | Implementation, architecture, code review |
| PM Agent (`agent.py`) | Sprint planning, status reports, risk tracking |
| User | Product decisions, go/no-go gates, scope changes |
