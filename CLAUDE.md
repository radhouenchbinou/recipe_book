# CLAUDE.md — Trading Bot Project Work Contract

This file defines how Claude Code operates on this repository.
Every session **must** follow these rules without exception.

---

## Project Identity

**Name:** AI-Powered Trading Bot
**Branch:** `claude/trading-bot-project-planning-HUmPC`
**Phase:** 1 of 3 (5 weeks)
**Goal:** Automated stock/ETF/gold trading with Claude API recommendations, sentiment analysis, and geopolitical risk scoring.

---

## Repository Structure

```
.
├── CLAUDE.md              ← this file (work contract)
├── agent.py               ← PM agent CLI
├── config.py              ← agent configuration
├── prompts.py             ← agent prompts
├── requirements.txt       ← Python dependencies
├── api/                   ← Node.js Express REST API
│   ├── src/
│   │   ├── routes/        ← endpoint handlers
│   │   ├── middleware/    ← auth, logging, error handling
│   │   └── services/      ← business logic
│   ├── package.json
│   └── Dockerfile
├── bot/                   ← Python trading bot engine
│   ├── collectors/        ← market data + news fetchers
│   ├── analysis/          ← indicators, sentiment, geo risk
│   ├── claude/            ← Claude API integration
│   ├── broker/            ← Alpaca connector
│   ├── scheduler/         ← APScheduler jobs
│   ├── main.py
│   └── Dockerfile
├── dashboard/             ← React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/      ← API client
│   ├── package.json
│   └── Dockerfile
└── infra/                 ← Docker Compose + K8s manifests
    ├── docker-compose.yml
    ├── docker-compose.prod.yml
    └── postgres/
        └── schema.sql
```

---

## Sprint Plan (Phase 1)

| Sprint | Week | Focus |
|--------|------|-------|
| 1 | Week 1 | Docker env · DB schema · Data pipeline · Broker connector |
| 2 | Week 2 | Technical indicators · Sentiment · Geo risk scoring |
| 3 | Week 3 | Claude API integration · Smart trigger · Fallback recommender |
| 4 | Week 4 | REST API endpoints · React dashboard |
| 5 | Week 5 | CI/CD · Load testing · Security · Monitoring · Go/No-Go |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Bot Engine | Python 3.11, APScheduler, TA-Lib, FinBERT |
| API Server | Node.js 20, Express 4, JWT auth |
| Frontend | React 18, Vite, Recharts |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Broker | Alpaca Markets API (paper trading in Phase 1) |
| AI | Anthropic Claude API (`claude-sonnet-4-6`) |
| Infra | Docker Compose (dev), Kubernetes (prod) |

---

## Environment Variables

Never hardcode secrets. All credentials go in `.env` (gitignored).

```
# Broker
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Claude
ANTHROPIC_API_KEY=...

# Database
DATABASE_URL=postgresql://trader:trader@localhost:5432/tradingbot

# Redis
REDIS_URL=redis://localhost:6379

# API
JWT_SECRET=...
API_PORT=3000

# Bot
BOT_ENV=development
CLAUDE_DAILY_CALL_BUDGET=0.25   # max 25% of daily Claude quota
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
- `eslint` + `prettier` enforced
- All routes must have input validation (`zod`)
- All endpoints must return `{ data, error, meta }` envelope
- HTTP responses: 200/201 success, 400 validation, 401 auth, 500 server error

### React (dashboard/)
- Functional components only; no class components
- `TypeScript` strict mode
- `react-query` for all server state
- No inline styles; use CSS modules or Tailwind

### General
- No secrets in code or git history
- Every PR must have tests
- Commit messages: `type(scope): short description` (e.g. `feat(bot): add RSI indicator`)

---

## Commands

```bash
# Start all services
docker-compose -f infra/docker-compose.yml up

# Run bot locally
cd bot && python main.py

# Run API locally
cd api && npm run dev

# Run dashboard locally
cd dashboard && npm run dev

# Run all Python tests
cd bot && pytest --cov=. --cov-report=term-missing

# Run API tests
cd api && npm test

# DB migrations
cd bot && alembic upgrade head
cd bot && alembic downgrade -1

# PM agent
python agent.py                             # interactive
python agent.py --action plan_phase1        # generate plan
python agent.py --action sprint_tasks --sprint 2
python agent.py --action status_report --week 1
```

---

## Git Workflow

- **Always develop on:** `claude/trading-bot-project-planning-HUmPC`
- **Never push to main** without explicit permission
- Commit after every meaningful unit of work
- Push at end of every session
- Commit format: `type(scope): message`
  - Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `ci`

---

## Decision Gates

Before advancing to the next sprint, **all** gate criteria must pass:

| Gate | Sprint → Sprint | Blocker if failed |
|------|-----------------|-------------------|
| G1 | S1 → S2 | Docker up, DB schema complete, data flowing, Alpaca connected |
| G2 | S2 → S3 | All 3 score types producing values, tests green |
| G3 | S3 → S4 | Claude recommendations working, fallback tested, usage capped |
| G4 | S4 → S5 | API <200ms p99, dashboard showing live data |
| G5 | S5 → Prod | CI green, load test passed, security audit clean |

---

## Non-Negotiables

1. **Paper trading only** in Phase 1 — no real money API calls
2. **Claude usage cap** — never exceed 30% of daily quota without explicit approval
3. **Tests before merge** — no code merged without passing tests
4. **No `.env` in git** — ever
5. **Structured logging** — all services must emit JSON logs
6. **Health endpoints** — every service must expose `/health`

---

## Contacts / Roles

| Role | Responsibility |
|------|---------------|
| Claude Code | Implementation, architecture, code review |
| PM Agent (`agent.py`) | Sprint planning, status reports, risk tracking |
| User | Product decisions, go/no-go gates, scope changes |
