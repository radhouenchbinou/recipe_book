# Trading Bot — Technical Architecture

**Version:** 2.0 — Updated after alignment sprint
**Date:** 2026-03-07
**Stack:** Python 3.11 · Node.js 20 · React 18 · PostgreSQL 15 · Redis 7 · RabbitMQ 3.13

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Infrastructure & Services](#2-infrastructure--services)
3. [Database Schema](#3-database-schema)
4. [Bot Engine (Python)](#4-bot-engine-python)
5. [API Server (Node.js)](#5-api-server-nodejs)
6. [Dashboard (React)](#6-dashboard-react)
7. [Communication Channels](#7-communication-channels)
8. [Security Model](#8-security-model)
9. [Complete Workflow — From Market Close to Open Position](#9-complete-workflow--from-market-close-to-open-position)

---

## 1. System Overview

The trading bot is a **5-service event-driven system** that autonomously collects market data, runs multi-factor analysis, asks Claude AI for trade recommendations, and executes paper trades via Alpaca Markets. Users monitor everything in real-time through a React dashboard.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL WORLD                                   │
│  Yahoo Finance  ·  RSS News Feeds  ·  Alpaca API  ·  Anthropic Claude  │
└───────┬──────────────────┬─────────────────┬──────────────────┬────────┘
        │ OHLCV data       │ news articles   │ orders/positions │ AI recs
        ▼                  ▼                 ▼                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       BOT ENGINE  (Python 3.11)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Collectors   │  │ Analysis     │  │ Claude       │  │ Broker   │ │
│  │ market_data  │  │ Technical    │  │ 3-turn conv. │  │ Alpaca / │ │
│  │ news_fetcher │  │ Sentiment    │  │ Fallback     │  │ IB       │ │
│  │              │  │ Geo Risk     │  │ Usage cap    │  │          │ │
│  │              │  │ Fundamentals │  │              │  │          │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────────┘ │
│         └─────────────────┴──────────────────┘                        │
│                           │ writes to DB                               │
│                           │ publishes to RabbitMQ                      │
└───────────────────────────┼───────────────────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
     ┌───────────┐   ┌────────────┐   ┌──────────────────┐
     │ PostgreSQL│   │  RabbitMQ  │   │    Redis         │
     │ (13 tables│   │ topic      │   │  read cache      │
     │  of state)│   │ exchange   │   │  (30-300s TTL)   │
     └─────┬─────┘   └─────┬──────┘   └────────┬─────────┘
           │               │                    │
           ▼               ▼                    │
┌──────────────────────────────────────────┐    │
│            API SERVER  (Node.js 20)      │◄───┘
│  Express + Socket.io + amqplib consumer  │
│  ┌──────────────────────────────────┐    │
│  │ Routes                           │    │
│  │  /auth  /portfolio  /market-data │    │
│  │  /recommendations  /alerts       │    │
│  │  /settings                       │    │
│  └──────────────────────────────────┘    │
│  Socket.io rooms: recs | market | alerts │
└──────────────────────┬───────────────────┘
                       │ REST + WebSocket
                       ▼
┌──────────────────────────────────────────┐
│          DASHBOARD  (React 18)           │
│  Zustand stores · react-query · Socket.io│
│  Portfolio · Recommendations · Market   │
│  Alerts · Analysis · Settings           │
└──────────────────────────────────────────┘
```

---

## 2. Infrastructure & Services

Six Docker containers orchestrated by Docker Compose:

| Service | Image | Port | Role |
|---------|-------|------|------|
| `postgres` | postgres:15-alpine | 5432 | Primary datastore (13 tables) |
| `redis` | redis:7-alpine | 6379 | API read cache (30-300s TTL) |
| `rabbitmq` | rabbitmq:3.13-management | 5672 / 15672 | Event bus between bot and API |
| `api` | Custom Node.js 20 | 3000 | REST API + Socket.io + RabbitMQ consumer |
| `bot` | Custom Python 3.11 | 8080 (health) | Analysis engine + scheduler |
| `dashboard` | Custom React/nginx | 8080 | SPA frontend |

**Startup order** (healthcheck-gated):
```
postgres (healthy) ─┐
redis    (healthy) ─┼──► api (starts) ──► dashboard
rabbitmq (healthy) ─┘
                    └──► bot (starts)
```

**Key environment variables:**

```bash
# Broker
ALPACA_API_KEY / ALPACA_SECRET_KEY
ALPACA_BASE_URL=https://paper-api.alpaca.markets   # paper only in Phase 1
BROKER=alpaca                                       # or "ib" for Interactive Brokers

# AI
ANTHROPIC_API_KEY
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_DAILY_CALL_BUDGET=0.25                       # max 25% of daily token quota

# Auth
JWT_SECRET                                          # signs 15-min access tokens

# Messaging
RABBITMQ_URL=amqp://trader:trader@rabbitmq:5672

# Notifications (optional)
SLACK_WEBHOOK_URL / SENDGRID_API_KEY / TWILIO_ACCOUNT_SID
```

---

## 3. Database Schema

13 tables in PostgreSQL. Grouped by domain:

### 3.1 Market Data

```
symbols          ← tracked instruments (SPY, QQQ, GLD, AAPL, MSFT, NVDA)
market_data      ← daily OHLCV snapshots (keyed by symbol_id + trade_date)
news_items       ← fetched RSS articles
news_symbols     ← junction: which article mentions which symbol
```

### 3.2 Analysis & Recommendations

```
analysis_scores  ← per-symbol composite scores + indicator snapshot (JSONB)
                   Fields: technical_score, sentiment_score, geo_risk_score,
                           composite_score, indicator_snapshot
recommendations  ← final action (buy/sell/hold) + confidence + reasoning
                   source: "claude" | "fallback"
claude_usage     ← token budget enforcement (daily)
```

### 3.3 Users & Auth

```
users            ← accounts (bcrypt password, role: admin | trader | viewer)
refresh_tokens   ← one row per active session (SHA-256 hash, 30-day TTL)
user_settings    ← notification prefs (Slack, Email, SMS) + risk tolerance
```

### 3.4 Operations

```
alerts           ← user-defined triggers (price_above, score_above, etc.)
bot_runs         ← scheduler audit log (status, symbols scanned, Claude calls)
position_history ← daily P&L snapshots for charting
```

### Entity Relationships

```
symbols ──< market_data
symbols ──< news_symbols >── news_items
symbols ──< analysis_scores
symbols ──< recommendations ──> analysis_scores
symbols ──< alerts
symbols ──< position_history
users ──< refresh_tokens
users ─── user_settings
```

---

## 4. Bot Engine (Python)

### 4.1 Scheduler — 4 Cron Jobs

```
APScheduler (BlockingScheduler, timezone: America/New_York)

6:00 PM ET  (weekdays)  ──► job_fetch_market_data()
Every 30min (always)    ──► job_fetch_news()
6:30 PM ET  (weekdays)  ──► job_run_analysis()
6:45 PM ET  (weekdays)  ──► job_run_recommendations()
```

Jobs run sequentially (each depends on the previous).

### 4.2 Data Collection

**market_data.py** — `fetch_all_symbols()`
- Downloads OHLCV data from Yahoo Finance via `yfinance`
- Upserts into `market_data` table (unique on `symbol_id + trade_date`)
- Protected by `CircuitBreaker("yfinance", failure_threshold=5, recovery_timeout=60)`

**news_fetcher.py** — `fetch_news()`
- Parses RSS feeds from financial news sources via `feedparser`
- Tags articles to symbols based on keyword matching
- Inserts into `news_items` + `news_symbols`

### 4.3 Analysis Pipeline

`run_analysis_pipeline()` calls `analyze_symbol(ticker)` for each of 6 tracked symbols:

```
analyze_symbol("AAPL")
  │
  ├─ compute_indicators(ticker)           ← RSI-14, MACD, Bollinger %B, SMA/EMA
  │    uses: market_data table (last 60 days)
  │    returns: IndicatorSnapshot + technical_score (0-100)
  │
  ├─ compute_sentiment_score(ticker)      ← FinBERT on recent news headlines
  │    uses: news_items for this ticker (last 24h)
  │    returns: float in [-1, +1]
  │
  ├─ compute_geo_risk_score(ticker)       ← geo event detection (keywords)
  │    scans: news headlines for geopolitical terms
  │    returns: GeoRiskResult (0-100, higher = riskier)
  │
  ├─ FundamentalAnalyzer.analyze(ticker)  ← yfinance .info (P/E, EPS, D/E, ROE)
  │    returns: FundamentalScore (0-100) or None (e.g. gold ETFs)
  │
  ├─ compute_composite_score(...)
  │    weights: Technical 35% · Sentiment 30% · Geo-risk inverse 20% · Fundamental 15%
  │    returns: 0-100 float
  │
  ├─ _persist_scores() → INSERT INTO analysis_scores
  │
  └─ _publish_analysis_done() → RabbitMQ "analysis.done" event
```

### 4.4 Recommendation Pipeline

`run_recommendation_pipeline()` calls `recommend_for_ticker(ticker)` for each symbol:

```
recommend_for_ticker("AAPL")
  │
  ├─ _load_latest_scores()    ← SELECT latest analysis_scores row for ticker
  │
  ├─ get_previous_composite() ← SELECT second-most-recent row (for delta)
  │
  ├─ should_call_claude()     ← Smart trigger (3 rules):
  │    Rule 1: budget check    → can_call_claude(est. 2500 tokens)?
  │    Rule 2: delta check     → |composite - previous| >= 5.0 pts?
  │    Rule 3: neutrality      → composite outside [42, 58]?
  │    → returns (True/False, reason)
  │
  ├─── IF should_call == True ──────────────────────────────────────────────┐
  │    get_recommendation(ctx) — 3-turn Claude conversation:                │
  │                                                                          │
  │    Turn 1 ─► "Summarise the key technical + fundamental signals"        │
  │              (max 300 tokens) — builds: RSI, MACD, scores block         │
  │    Claude ◄─ "RSI at 72 signals overbought; MACD histogram declining…"  │
  │                                                                          │
  │    Turn 2 ─► "Identify the primary risks"                               │
  │              (max 300 tokens) — references turn 1 analysis              │
  │    Claude ◄─ "1. Overbought technicals may trigger mean reversion…"     │
  │                                                                          │
  │    Turn 3 ─► "Provide final JSON recommendation"                        │
  │              (max 512 tokens)                                            │
  │    Claude ◄─ { "action": "hold", "confidence": 0.72, ... }             │
  │                                                                          │
  │    record_usage() → INSERT INTO claude_usage (token count)              │
  │    parse_response() → validate JSON, extract fields                     │
  │    persist_recommendation() → INSERT INTO recommendations               │
  │    publish "rec.new" → RabbitMQ                                         │
  │    return Recommendation                                        ─────────┘
  │
  └─── IF should_call == False ─────────────────────────────────────────────┐
       generate_fallback_recommendation()                                    │
         composite > 65 → buy  (confidence ~ 0.60-0.80)                    │
         composite < 35 → sell (confidence ~ 0.60-0.80)                    │
         else           → hold                                              │
       persist_recommendation(source="fallback") → DB                       │
       return Recommendation                                        ─────────┘
```

### 4.5 Broker Abstraction

```
BaseBroker (ABC)
  ├── AlpacaBroker   ← alpaca-trade-api REST (paper: paper-api.alpaca.markets)
  └── IBBroker       ← ib_insync (TWS paper port 7497)

get_broker() factory reads BROKER env var (default: "alpaca")
```

All broker calls are protected by retry logic (tenacity, 3 attempts, exponential backoff).

### 4.6 Circuit Breaker

Wraps all external I/O:

```
State machine: CLOSED ──[5 failures]──► OPEN ──[60s timeout]──► HALF_OPEN
                  ▲                                                    │
                  └──────────────[2 successes]───────────────────────┘

Applied to:
  yfinance downloads    → CircuitBreaker("yfinance")
  RSS feed fetches      → CircuitBreaker("news")
  Anthropic API calls   → CircuitBreaker("claude")
  Alpaca API calls      → CircuitBreaker("alpaca")
```

### 4.7 Notification Worker

Separate process (`python -m bot.workers.notification_worker`) consuming RabbitMQ:

```
notify.slack  ──► SlackNotifier  → POST webhook URL
notify.email  ──► EmailNotifier  → SendGrid transactional API
notify.sms    ──► SMSNotifier    → Twilio Messages API
```

Triggered when: high-confidence recommendation generated, alert fires, or bot error.

---

## 5. API Server (Node.js)

### 5.1 Middleware Stack

```
Request
  │
  ├─ helmet()           ← security headers
  ├─ cors()             ← CORS (credentials: true for cookie)
  ├─ rateLimit()        ← global: 300 req/min per IP
  ├─ express.json()     ← body parsing (1 MB limit)
  ├─ cookieParser()     ← reads HttpOnly refresh_token cookie
  ├─ logger             ← structured JSON request logging
  │
  ├─ requireAuth()      ← verifies Bearer JWT (15-min access token)
  ├─ userLimiter()      ← per-user: 100 req/min (keyed by user.sub)
  │
  └─ route handler
```

### 5.2 REST Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/auth/register` | — | — | Create account (bcrypt, seed user_settings) |
| POST | `/auth/login` | — | — | Issue 15-min JWT + 30-day refresh cookie |
| POST | `/auth/refresh` | cookie | — | Rotate refresh token, issue new JWT |
| POST | `/auth/logout` | Bearer | any | Delete refresh token, clear cookie |
| GET | `/health` | — | — | Postgres + Redis connectivity |
| GET | `/api/v1/portfolio` | Bearer | any | Alpaca account summary (cache 30s) |
| GET | `/api/v1/portfolio/positions` | Bearer | any | Open positions (cache 30s) |
| GET | `/api/v1/recommendations` | Bearer | any | Paginated feed (filter: symbol, source, action) |
| GET | `/api/v1/recommendations/:symbol` | Bearer | any | Latest for one symbol |
| GET | `/api/v1/market-data/:symbol` | Bearer | any | OHLCV + scores (cache 300s) |
| GET | `/api/v1/alerts` | Bearer | any | All alerts for account |
| POST | `/api/v1/alerts` | Bearer | any | Create alert |
| DELETE | `/api/v1/alerts/:id` | Bearer | admin/trader | Delete alert |
| PATCH | `/api/v1/alerts/:id` | Bearer | any | Toggle active/inactive |
| GET | `/api/v1/settings` | Bearer | any | User notification preferences |
| PATCH | `/api/v1/settings` | Bearer | any | Update preferences |

All responses use envelope: `{ data, error, meta }`.

### 5.3 Redis Caching

```
Cache key                          TTL      Endpoint
portfolio:account                  30s      GET /api/v1/portfolio
portfolio:positions                30s      GET /api/v1/portfolio/positions
recs:{sym}:{src}:{action}:{l}:{o}  60s      GET /api/v1/recommendations
market:{ticker}:{days}             300s     GET /api/v1/market-data/:symbol
```

Cache miss → DB query → cache write. Redis failure is non-fatal (falls through to DB).

### 5.4 Socket.io (Real-time)

```
Connection: ws://api:3000
Auth: socket.handshake.auth.token = JWT access token

Client joins rooms:
  socket.emit("join", "recs")    ← recommendations page
  socket.emit("join", "market")  ← market page
  socket.emit("join", "alerts")  ← alerts page

Events pushed to rooms:
  recs    ← "newRecommendation"  { symbol, action, confidence, id }
  market  ← "scoresUpdated"      { symbol, composite }
  alerts  ← "alertTriggered"     { symbol, alert_type, threshold }
```

### 5.5 RabbitMQ Consumer

Starts at boot inside `consumer.js`, subscribes to `trading.events` topic exchange:

```
Routing key     → Socket.io room  → Event name
rec.new         → recs            → newRecommendation
analysis.done   → market          → scoresUpdated
alert.trigger   → alerts          → alertTriggered
```

---

## 6. Dashboard (React)

### 6.1 State Architecture

Two complementary state layers:

```
Server state (react-query)          Client state (Zustand)
─────────────────────────           ──────────────────────────────
Cached, refetched on interval       Instant UI updates (no server round-trip)
Handles loading/error states        Synced with Socket.io push events

usePortfolio()   ← /portfolio       portfolioStore  ← live position updates
useMarketData()  ← /market-data     marketStore     ← real-time price quotes
useNotifications ← mutation states  alertStore      ← alert toggling
                                     analysisStore   ← score cards
                                     authStore       ← JWT + user (persisted)
```

### 6.2 Pages

| Page | Data source | Real-time |
|------|-------------|-----------|
| Portfolio | GET /api/v1/portfolio + /positions | No (30s poll) |
| Recommendations | GET /api/v1/recommendations | Yes — `newRecommendation` event |
| Market | GET /api/v1/market-data/:symbol | Yes — `scoresUpdated` event |
| Alerts | GET /api/v1/alerts | Yes — `alertTriggered` event |
| Analysis | GET /api/v1/market-data per symbol | Yes — `scoresUpdated` event |
| Settings | GET/PATCH /api/v1/settings | No |

### 6.3 Auth Flow

```
1. User submits login form
   POST /auth/login { username, password }
   ← 200 { data: { token, user } } + Set-Cookie: refresh_token (HttpOnly)

2. token saved in authStore (Zustand, persisted to localStorage)
   user info stored in authStore

3. Every request: axios interceptor reads authStore.token
   → Authorization: Bearer <15-min JWT>

4. On 401 response: axios interceptor auto-calls POST /auth/refresh
   → reads refresh_token cookie (sent automatically by browser)
   ← new 15-min JWT
   → retries original request with new token

5. Logout: POST /auth/logout → server deletes refresh_token row
   → clearAuth() clears Zustand store → socket.disconnect()
```

---

## 7. Communication Channels

### Between Components

```
Bot ──────────────────────────────► PostgreSQL ◄─────────────── API
(writes market_data, analysis_scores,          (reads for REST responses)
 recommendations, claude_usage)

Bot ──────────────────────────────► RabbitMQ ────────────────► API (consumer.js)
(publishes: rec.new, analysis.done,           (subscribes, emits Socket.io)
 alert.trigger, notify.*)

API ─────────────────────────────── Redis ────────────────────► API
(writes cache after DB reads)                 (reads cache before DB)

API ──────────────────────────────► Socket.io ───────────────► Dashboard
(server push: newRecommendation,              (React hooks receive events)
 scoresUpdated, alertTriggered)

Dashboard ───────────────────────► API (REST) ◄──────────────── Bot
(user actions: create alert, update                             (never calls API)
 settings, request data)
```

### RabbitMQ Exchange Details

```
Exchange: trading.events (topic, durable)

Routing key     Published by          Consumed by
──────────────  ────────────────────  ──────────────────────────────────
rec.new         claude/parser.py      api/src/consumer.js → Socket.io
analysis.done   analysis/pipeline.py  api/src/consumer.js → Socket.io
alert.trigger   scheduler/jobs.py     api/src/consumer.js → Socket.io
notify.slack    scheduler/jobs.py     bot/workers/notification_worker.py
notify.email    scheduler/jobs.py     bot/workers/notification_worker.py
notify.sms      scheduler/jobs.py     bot/workers/notification_worker.py
```

---

## 8. Security Model

### Authentication

```
Access token:  JWT, HS256, 15-minute lifetime
               Payload: { sub: user.id, username, role, iat, exp }
               Sent as: Authorization: Bearer <token>

Refresh token: 48-byte cryptographically random, SHA-256 hashed in DB
               Lifetime: 30 days
               Sent as: HttpOnly Secure SameSite=Strict cookie (path: /auth/refresh)
               Rotation: each use invalidates old token, issues new one
```

### Authorization (RBAC)

```
Role       Permissions
────────   ──────────────────────────────────────────────
admin      All endpoints + DELETE /api/v1/alerts/:id
trader     All read + create/patch alerts + settings
viewer     Read-only (portfolio, recommendations, market)
```

### Rate Limiting

```
Layer 1 (IP):   300 req/min — all traffic
Layer 2 (user): 100 req/min — authenticated /api/* routes (keyed by user.id)
```

### Passwords

bcrypt with cost factor 12 (~250ms hash time, brute-force resistant).

### Non-Negotiables

1. **Paper trading only** — `ALPACA_BASE_URL` must point to `paper-api.alpaca.markets`
2. **Claude budget cap** — never exceed 25% of daily token quota (`CLAUDE_DAILY_CALL_BUDGET=0.25`)
3. **No `.env` in git** — all secrets via environment variables
4. **Structured JSON logging** — all services emit `{ level, msg, ... }`

---

## 9. Complete Workflow — From Market Close to Open Position

This traces the complete lifecycle of a **BUY recommendation for AAPL** that results in an open position.

```
TIMELINE (Eastern Time, weekday)
═════════════════════════════════════════════════════════════════════════
4:00 PM  Market closes (US equity session ends)
6:00 PM  APScheduler fires: job_fetch_market_data
6:30 PM  APScheduler fires: job_run_analysis
6:45 PM  APScheduler fires: job_run_recommendations
~6:46 PM  Trade executed (paper)
```

---

### Step 1 — Market Data Collection (6:00 PM)

```
bot/scheduler/jobs.py
  └─► job_fetch_market_data()
        └─► collectors/market_data.fetch_all_symbols()
              │
              ├─ For each ticker in [SPY, QQQ, GLD, AAPL, MSFT, NVDA]:
              │    CircuitBreaker("yfinance").call(
              │      yf.Ticker("AAPL").history(period="1d")
              │    )
              │    ← { Open: 184.20, High: 187.10, Low: 183.90,
              │         Close: 185.50, Volume: 52_348_000 }
              │
              └─► INSERT INTO market_data
                    (symbol_id, trade_date, open, high, low, close, volume)
                  ON CONFLICT (symbol_id, trade_date) DO UPDATE ...
```

**DB state after step 1:**
```sql
market_data: { symbol: AAPL, trade_date: 2026-03-07, close: 185.50, ... }
```

---

### Step 2 — News Collection (every 30 minutes, running in parallel)

```
bot/collectors/news_fetcher.fetch_news()
  │
  ├─ Fetch RSS feeds (feedparser) from financial news sources
  │    CircuitBreaker("news").call(feedparser.parse, feed_url)
  │
  ├─ Extract headlines, summaries, published dates
  │
  ├─ Tag articles to symbols:
  │    headline: "Apple reports record iPhone sales ahead of WWDC"
  │    → matched to AAPL
  │
  └─► INSERT INTO news_items { headline, summary, url, published_at }
      INSERT INTO news_symbols { news_id, symbol_id: AAPL_UUID }
```

---

### Step 3 — Analysis Pipeline (6:30 PM)

```
bot/analysis/pipeline.run_analysis_pipeline()
  └─► analyze_symbol("AAPL")
        │
        ├─[1] compute_indicators("AAPL")
        │       Queries: SELECT close FROM market_data WHERE ticker=AAPL ORDER BY trade_date DESC LIMIT 60
        │       Computes:
        │         RSI-14:        58.3   (neutral, trending up)
        │         MACD:         +0.45   (bullish crossover)
        │         MACD hist:    +0.12   (momentum building)
        │         Bollinger %B:  0.72   (approaching upper band)
        │         SMA-20:       182.10
        │         EMA-12:       184.80
        │         technical_score = 72.4 / 100
        │
        ├─[2] compute_sentiment_score("AAPL")
        │       Queries: news_items for AAPL in last 24h
        │       FinBERT tokenizes + classifies each headline:
        │         "Apple record iPhone sales" → positive (0.89)
        │         "Fed rate hike concerns"   → negative (0.61) — tagged to all
        │       Weighted average → sentiment_score = +0.42
        │
        ├─[3] compute_geo_risk_score("AAPL")
        │       Scans news for geo keywords: ["tariff", "sanction", "conflict", ...]
        │       Detected: "US-China trade tensions" (weight: 15 pts)
        │       geo_risk_score = 22.0 / 100
        │
        ├─[4] FundamentalAnalyzer.analyze("AAPL")
        │       yfinance Ticker("AAPL").info:
        │         trailingPE:              28.4    → PE score: 62/100
        │         earningsQuarterlyGrowth:  0.13   → EPS score: 63/100
        │         revenueGrowth:            0.08   → Rev score: 58/100
        │         debtToEquity:           180.0    → D/E score: 55/100  (1.8x)
        │         returnOnEquity:           1.47   → ROE score: 100/100 (147%)
        │       fundamental_score = 66.8 / 100
        │
        ├─[5] compute_composite_score(72.4, +0.42, 22.0, 66.8)
        │       sent_scaled  = (0.42 + 1) / 2 × 100 = 71.0
        │       geo_inverted = 100 - 22.0 = 78.0
        │
        │       composite = 0.35 × 72.4   (technical)
        │                 + 0.30 × 71.0   (sentiment)
        │                 + 0.20 × 78.0   (geo-risk inverted)
        │                 + 0.15 × 66.8   (fundamental)
        │                = 25.34 + 21.30 + 15.60 + 10.02
        │                = 72.26 / 100
        │
        ├─[6] INSERT INTO analysis_scores
        │       { symbol_id: AAPL_UUID, composite: 72.26,
        │         technical: 72.4, sentiment: 0.42,
        │         geo_risk: 22.0,
        │         indicator_snapshot: { rsi_14: 58.3, macd: 0.45, ... } }
        │
        └─[7] publish → RabbitMQ "analysis.done"
                { symbol: "AAPL", composite: 72.26 }
                  │
                  └─► API consumer.js receives "analysis.done"
                      io.to("market").emit("scoresUpdated", { symbol: "AAPL", composite: 72.26 })
                        │
                        └─► Dashboard MarketPage updates AAPL score card in real-time
```

**DB state after step 3:**
```sql
analysis_scores: { ticker: AAPL, composite: 72.26, technical: 72.4,
                   sentiment: 0.42, geo_risk: 22.0 }
```

---

### Step 4 — Recommendation Pipeline (6:45 PM)

```
bot/claude/recommender.recommend_for_ticker("AAPL")
  │
  ├─[1] _load_latest_scores("AAPL")
  │       → composite: 72.26, close: 185.50, score_id: <UUID>
  │
  ├─[2] get_previous_composite("AAPL")
  │       → previous: 65.40   (from yesterday)
  │
  ├─[3] should_call_claude(composite=72.26, previous=65.40)
  │       Budget check:    can_call_claude(2500 tokens)?  → YES (used 8% today)
  │       Delta check:     |72.26 - 65.40| = 6.86 >= 5.0 → YES (threshold met)
  │       Neutrality:      72.26 is outside [42, 58]      → YES (actionable)
  │       → (True, "score_actionable")
  │
  └─[4] 3-turn Claude conversation:
```

```
Turn 1 ──────────────────────────────────────────────────────────────────
User: "Analyse the following data for AAPL as of 2026-03-07 and summarise
       the 2-3 most significant technical and fundamental signals…

       Ticker: AAPL | Price: $185.50 | Date: 2026-03-07
       Scores: Technical: 72.4 | Fundamental: unavailable | Sentiment: +0.420
               Geo risk: 22.0 | Composite: 72.3 (↑ 6.9 pts)
       Indicators: RSI-14: 58.3 | MACD: 0.4500 | MACD hist: 0.1200 | BB %B: 0.720
       Geo events: none detected"

Claude: "AAPL shows a bullish MACD crossover with a rising histogram (+0.12),
         indicating accelerating upside momentum. RSI at 58.3 is in healthy
         mid-range territory — not yet overbought. The Bollinger %B at 0.72
         suggests price is trending toward the upper band with room to run.
         Composite score jumped +6.9 points, the largest single-session move
         in two weeks."

(input: 287 tokens, output: 89 tokens)
```

```
Turn 2 ──────────────────────────────────────────────────────────────────
User: "Given your signal analysis above, identify the 2-3 primary risks
       that could invalidate a bullish thesis for AAPL."

Claude: "1. RSI approaching 60 — a continued rise above 70 would signal
            overbought conditions and increase mean-reversion risk.
         2. US-China trade tensions flagged in geo-risk scoring (22/100)
            could impact AAPL's supply chain and demand in China market.
         3. Bollinger %B at 0.72 means price is 72% of the way to the upper
            band — a rejection at the upper band could trigger a pullback."

(input: 408 tokens, output: 94 tokens)
```

```
Turn 3 ──────────────────────────────────────────────────────────────────
User: "Based on your signal analysis and risk assessment above, provide
       the final trading recommendation in this exact JSON format…"

Claude: {
  "action": "buy",
  "confidence": 0.74,
  "reasoning": "Strong MACD crossover with rising histogram and composite
                 score at 72.3 (up 6.9 pts) signal bullish momentum.
                 Fundamentals support valuation despite premium P/E.
                 Geo risk manageable at 22/100.",
  "key_risks": [
    "RSI approaching overbought territory above 60",
    "US-China trade tension supply-chain exposure"
  ],
  "suggested_position_size": 0.07
}

(input: 521 tokens, output: 108 tokens)
Total tokens this call: 1407 input + 291 output = 1698 tokens
```

```
  ├─[5] record_usage()
  │       INSERT INTO claude_usage
  │         { input_tokens: 1407, output_tokens: 291, symbol: AAPL,
  │           trigger_reason: "multi_turn_analysis" }
  │
  ├─[6] parse_response() → validate JSON, extract fields
  │       action: "buy" ✓ (in VALID_ACTIONS)
  │       confidence: 0.74 ✓ (between 0 and 1)
  │       reasoning: string ✓
  │
  ├─[7] persist_recommendation()
  │       INSERT INTO recommendations
  │         { symbol_id: AAPL_UUID, score_id: <UUID>, action: "buy",
  │           confidence: 0.74, reasoning: "...", source: "claude",
  │           raw_response: { raw: "...", key_risks: [...],
  │                           suggested_position_size: 0.07 } }
  │
  └─[8] publish → RabbitMQ "rec.new"
          { symbol: "AAPL", action: "buy", confidence: 0.74, id: <UUID> }
```

**DB state after step 4:**
```sql
recommendations: { ticker: AAPL, action: buy, confidence: 0.74,
                   source: claude, suggested_position_size: 0.07 }
```

---

### Step 5 — Real-time Push to Dashboard

```
RabbitMQ "rec.new" event
  └─► api/src/consumer.js
        └─► io.to("recs").emit("newRecommendation", {
              symbol: "AAPL", action: "buy", confidence: 0.74, id: "<UUID>"
            })
              │
              └─► Dashboard (any connected clients in "recs" room)
                    useWebSocket("recs", "newRecommendation", handler)
                    handler({ symbol: "AAPL", action: "buy", confidence: 0.74 })
                      │
                      ├─ queryClient.invalidateQueries(["recommendations"])
                      │   → triggers refetch → new rec appears in UI
                      │
                      └─ useNotifications().notify(
                           "New BUY recommendation for AAPL (74% confidence)",
                           "success"
                         )
                         → ToastContainer shows toast for 5 seconds
```

---

### Step 6 — Alert Evaluation (if configured)

```
User had configured: alert { symbol: AAPL, type: "recommendation", threshold: null }

scheduler/jobs.py (in recommendation job, after pipeline completes):
  For each active "recommendation" alert for AAPL:
    action == "buy" → alert condition met!

    PATCH alerts SET triggered_at = NOW() WHERE id = <alert_id>

    publish → RabbitMQ "alert.trigger"
      { symbol: "AAPL", alert_type: "recommendation", message: "BUY signal" }
        │
        └─► api/src/consumer.js
              io.to("alerts").emit("alertTriggered", { ... })
                └─► Dashboard AlertsPage: row highlights, toast fires

    publish → RabbitMQ "notify.slack" (if user has Slack enabled in user_settings)
      { title: "AAPL BUY Signal", body: "Confidence 74%", symbol: "AAPL" }
        │
        └─► bot/workers/notification_worker.py
              SlackNotifier.send("AAPL BUY Signal", "Confidence 74%", "AAPL")
              POST https://hooks.slack.com/services/... { text: "*[AAPL] AAPL BUY Signal*\nConfidence 74%" }
```

---

### Step 7 — Dashboard Viewing (User Experience)

```
User opens RecommendationsPage (or receives toast)

react-query fetches: GET /api/v1/recommendations?symbol=AAPL
  → API queries recommendations table
  → Redis cache miss (first fetch) → DB query → cache (60s TTL)
  ← 200 {
      data: [{
        ticker: "AAPL",
        action: "buy",
        confidence: 0.74,
        reasoning: "Strong MACD crossover with rising histogram...",
        source: "claude",
        key_risks: ["RSI approaching overbought...", "US-China..."],
        position_size: 0.07,
        recommended_at: "2026-03-07T23:45:12Z"
      }],
      meta: { total: 1, limit: 20, offset: 0 }
    }

User clicks "View Portfolio" → PortfolioPage
GET /api/v1/portfolio/positions
  ← 200 {
      data: [{
        symbol: "AAPL",
        qty: 37.0,
        market_value: 6863.50,
        cost_basis: 6742.40,
        unrealized_pl: +121.10,
        unrealized_pct: +1.80,
        current_price: 185.50,
        side: "long"
      }]
    }
```

Note: in Phase 1, the bot generates the recommendation but **does not auto-execute**. The position shown in the portfolio reflects a trade the user placed manually in Alpaca's paper trading interface after reviewing the recommendation.

---

### Step 8 — P&L Snapshot (next day)

```
scheduler/jobs.py (can be added to daily run):
  BrokerConnector.get_positions() → [Position(AAPL, qty=37, market_val=6980, unrealized_pl=237.6)]

  INSERT INTO position_history
    { symbol_id: AAPL_UUID, qty: 37, avg_entry: 182.23,
      market_val: 6980.00, unrealised_pnl: 237.60 }

PortfolioPage AnalysisPage reads position_history for P&L chart.
```

---

### End-to-End Summary

```
4:00 PM  Market closes
         └── NYSE/NASDAQ session ends

6:00 PM  [Bot] market_data job
         └── yfinance → OHLCV for 6 symbols → market_data table

6:30 PM  [Bot] analysis job (per symbol, ~45s total)
         ├── indicators    → RSI, MACD, Bollinger, SMA/EMA
         ├── FinBERT       → news sentiment score
         ├── geo_risk      → geopolitical event scan
         ├── fundamentals  → P/E, EPS, D/E, ROE via yfinance
         ├── composite     → weighted 0-100 score → analysis_scores table
         └── RabbitMQ "analysis.done" → API → Socket.io → dashboard update

6:45 PM  [Bot] recommendation job (per symbol, ~15s total for Claude path)
         ├── load scores   → analysis_scores DB read
         ├── trigger check → delta +6.9pts passes, budget OK, score actionable
         ├── Claude Turn 1 → signal summary (RSI, MACD, momentum)
         ├── Claude Turn 2 → risk identification
         ├── Claude Turn 3 → JSON recommendation: BUY @ 0.74 confidence
         ├── DB write      → recommendations table
         └── RabbitMQ "rec.new" → API → Socket.io → dashboard toast

~6:46 PM [Dashboard] real-time update received
         ├── newRecommendation event → recommendations list refreshes
         ├── toast: "New BUY for AAPL (74%)"
         └── alertTriggered → Slack notification sent (if configured)

~6:47 PM [User] reviews recommendation on dashboard
         ├── sees: BUY AAPL | Confidence 74% | Position size 7%
         ├── reads reasoning + key risks
         └── places paper trade manually in Alpaca dashboard

Next day [Bot] position_history job
         └── Alpaca positions → position_history snapshot for P&L chart
```

---

## Appendix — Technology Decisions

| Choice | Alternative considered | Reason kept |
|--------|----------------------|-------------|
| FinBERT for sentiment | VADER (arch. doc) | Finance-specific model; outperforms VADER on earnings/news text |
| `claude-sonnet-4-6` | Haiku (cheaper) | Better reasoning for multi-factor trading context |
| RabbitMQ (topic exchange) | Redis Pub/Sub | Durable messages, routing keys, management UI, dead-letter queues |
| Prometheus + Grafana | CloudWatch / DataDog | Self-hosted, no vendor lock-in, full control |
| Docker Compose | Kubernetes | Right-sized for 6-service Phase 1; ECS/K8s in Phase 2 |
| APScheduler | Celery | No broker required for scheduling; simpler for 4-job use case |
