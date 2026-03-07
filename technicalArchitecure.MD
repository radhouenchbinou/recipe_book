# Trading Bot - Technical Architecture Solution Proposition

**Document Version:** 1.0  
**Date:** March 2026  
**Purpose:** Present the chosen architecture with alternatives and justification

---

## 1. EXECUTIVE SUMMARY (For Decision Makers)

### Proposed Solution: Microservices Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│            Real-time Dashboard + Mobile Web                │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API + WebSocket
┌────────────────────▼────────────────────────────────────────┐
│                  API GATEWAY (Node.js)                      │
│         Authentication, Rate Limiting, Caching              │
└─┬──────────────────┬──────────────────┬────────────────────┘
  │                  │                  │
  ▼                  ▼                  ▼
┌──────────┐  ┌────────────┐  ┌──────────────┐
│Portfolio │  │Recommend.  │  │Notifications│
│Service   │  │Service     │  │Service       │
└──────────┘  └────────────┘  └──────────────┘
  │                  │                  │
  └──────────┬───────┴─────────────────┘
             │
    ┌────────▼──────────┐
    │   Bot Engine      │
    │   (Python)        │
    │ Analysis + Claude │
    └────────┬──────────┘
             │
    ┌────────▼──────────────┐
    │  Shared Services      │
    │ Database, Cache, APIs │
    └───────────────────────┘
```

**Why This Architecture:**
- ✅ Scales horizontally (multiple instances)
- ✅ Independent service deployment
- ✅ Stateless API (easier to scale)
- ✅ Separates concerns (analysis vs. delivery)
- ✅ Proven for financial systems
- ✅ Easy to test each component

---

## 2. ARCHITECTURAL OVERVIEW

### 2.1 Core Design Principles

```
Principle 1: Separation of Concerns
├─ Bot Engine: Pure analysis (no API/web code)
├─ API Layer: Data delivery (no trading logic)
├─ Dashboard: UI presentation (no business logic)
└─ Services: Specialized functions (single responsibility)

Principle 2: Stateless Design
├─ No in-memory state in API servers
├─ All state in PostgreSQL or Redis
├─ Allows horizontal scaling
├─ Enables zero-downtime deployments

Principle 3: Asynchronous Processing
├─ Long operations (analysis, Claude calls) run in background
├─ API responds immediately
├─ Results pushed via WebSocket
├─ Better user experience

Principle 4: Fault Tolerance
├─ Circuit breakers for external APIs
├─ Retry logic with exponential backoff
├─ Graceful degradation
├─ Health checks on all services
```

### 2.2 Architectural Layers

```
LAYER 1: PRESENTATION
┌────────────────────────────────┐
│ React SPA + Mobile Web         │
│ Real-time updates via Socket.io│
└────────────────────────────────┘

LAYER 2: API GATEWAY
┌────────────────────────────────┐
│ Express.js + Middleware        │
│ - Authentication (JWT)          │
│ - Rate limiting                 │
│ - CORS handling                │
│ - Request/response logging     │
│ - Error handling               │
└────────────────────────────────┘

LAYER 3: APPLICATION SERVICES
┌─────────────┬──────────┬───────────────┐
│ Portfolio   │ Analysis │ Notification  │
│ Service     │ Service  │ Service       │
├─────────────┼──────────┼───────────────┤
│ - Positions │ - Tech   │ - Slack       │
│ - P&L       │ - Fund   │ - Email       │
│ - Broker    │ - Sent.  │ - SMS         │
│ - Orders    │ - Geo    │ - Dashboard   │
└─────────────┴──────────┴───────────────┘

LAYER 4: BUSINESS LOGIC
┌────────────────────────────────┐
│ Python Bot Engine              │
│ - Data collection              │
│ - Technical analysis           │
│ - Fundamental analysis         │
│ - Sentiment analysis           │
│ - Geopolitical analysis        │
│ - Claude AI integration        │
│ - Recommendation generation    │
└────────────────────────────────┘

LAYER 5: DATA & INFRASTRUCTURE
┌──────────────┬─────────┬──────────┐
│ PostgreSQL   │ Redis   │ S3/Files │
│ - Relational │ - Cache │ - Logs   │
│ - Audit      │ - Queue │ - Backups│
│ - Reporting  │ - Pub/  │          │
│              │   Sub   │          │
└──────────────┴─────────┴──────────┘
```

---

## 3. DETAILED COMPONENT ARCHITECTURE

### 3.1 Frontend Architecture

```
React SPA (Single Page Application)
│
├─ Pages Layer
│  ├─ Dashboard
│  ├─ Portfolio
│  ├─ Recommendations
│  ├─ Analysis
│  ├─ Alerts
│  └─ Settings
│
├─ Components Layer
│  ├─ Charts (Recharts)
│  ├─ Tables
│  ├─ Forms
│  ├─ Modals
│  └─ Real-time Widgets
│
├─ State Management (Zustand)
│  ├─ portfolioStore
│  ├─ marketStore
│  ├─ analysisStore
│  ├─ alertStore
│  └─ authStore
│
├─ Services Layer
│  ├─ API service (axios)
│  ├─ WebSocket service (Socket.io)
│  ├─ Auth service
│  └─ Storage service
│
└─ Hooks
   ├─ usePortfolio()
   ├─ useMarketData()
   ├─ useWebSocket()
   ├─ useAuth()
   └─ useNotifications()

Real-time Updates via Socket.io:
├─ Price updates (every 5 sec)
├─ New recommendations (real-time)
├─ Alert triggers (immediate)
└─ Market condition changes
```

### 3.2 API Gateway (Node.js Express)

```
Express.js API Gateway
│
├─ Middleware Stack
│  ├─ CORS
│  ├─ Body Parser
│  ├─ Compression
│  ├─ Rate Limiter (100 req/min)
│  ├─ JWT Authentication
│  ├─ Error Handler
│  └─ Request Logger
│
├─ Routes
│  ├─ /auth/* (login, register, refresh)
│  ├─ /portfolio/* (positions, performance)
│  ├─ /market/* (prices, historical, technical)
│  ├─ /analysis/* (sentiment, geopolitical)
│  ├─ /recommendations/* (active, history)
│  ├─ /alerts/* (log, settings)
│  └─ /system/* (health, usage)
│
├─ Controllers
│  ├─ Portfolio Controller
│  ├─ Market Controller
│  ├─ Recommendation Controller
│  ├─ Alert Controller
│  └─ Auth Controller
│
├─ Middleware Functions
│  ├─ authenticate() - Verify JWT
│  ├─ authorize() - Check permissions
│  ├─ rateLimit() - Prevent abuse
│  ├─ cache() - Cache responses
│  └─ errorHandler() - Global error handling
│
└─ WebSocket Handler (Socket.io)
   ├─ Connection management
   ├─ Event listeners
   ├─ Broadcast handlers
   └─ Graceful disconnection
```

### 3.3 Python Bot Engine

```
Trading Bot Engine (Python)
│
├─ Main Entry Point
│  └─ main.py (APScheduler setup)
│
├─ Scheduler (APScheduler)
│  ├─ Every 4 hours: Quick analysis
│  ├─ Daily 4:30pm: Daily summary
│  └─ Friday 4:30pm: Weekly deep dive
│
├─ Data Collection Module
│  ├─ MarketDataCollector
│  │  ├─ Fetch from Yahoo Finance
│  │  ├─ Calculate indicators
│  │  └─ Store in PostgreSQL
│  │
│  ├─ NewsFetcher
│  │  ├─ Fetch financial news
│  │  ├─ Fetch geopolitical news
│  │  └─ Parse & store
│  │
│  └─ BrokerConnector
│     ├─ Alpaca API
│     ├─ Interactive Brokers API
│     └─ Position sync
│
├─ Analysis Module
│  ├─ TechnicalAnalyzer
│  │  ├─ Moving averages
│  │  ├─ RSI, MACD
│  │  ├─ Bollinger Bands
│  │  └─ Signal generation
│  │
│  ├─ FundamentalAnalyzer
│  │  ├─ P/E ratios
│  │  ├─ EPS growth
│  │  ├─ Valuation
│  │  └─ Quality scoring
│  │
│  ├─ SentimentAnalyzer
│  │  ├─ VADER sentiment scoring
│  │  ├─ Trend analysis
│  │  └─ Sentiment flip detection
│  │
│  └─ GeopoliticalAnalyzer
│     ├─ Event detection
│     ├─ Impact assessment
│     └─ Risk scoring
│
├─ AI Integration
│  ├─ AITriggerDecider
│  │  ├─ Volatility check
│  │  ├─ Sentiment flip detection
│  │  ├─ Geopolitical event check
│  │  └─ Technical signal check
│  │
│  └─ ClaudeClient
│     ├─ Multi-turn conversation
│     ├─ Cost tracking
│     └─ Error handling
│
├─ Recommendation Engine
│  ├─ RecommendationGenerator
│  │  ├─ Generate BUY/SELL/HOLD
│  │  ├─ Calculate entry/exit
│  │  ├─ Risk assessment
│  │  └─ Conviction levels
│  │
│  └─ RiskCalculator
│     ├─ Stop loss calculation
│     ├─ Profit target
│     └─ Position sizing
│
├─ Notification Module
│  ├─ SlackNotifier
│  ├─ EmailNotifier
│  ├─ SMSNotifier
│  └─ DashboardNotifier
│
└─ Database
   └─ ORM (SQLAlchemy)
      ├─ Query builder
      ├─ Connection pooling
      └─ Migration handling
```

### 3.4 Database Layer (PostgreSQL)

```
PostgreSQL Database
│
├─ Users & Authentication (Phase 2)
│  ├─ users
│  ├─ user_settings
│  └─ broker_accounts
│
├─ Trading Data
│  ├─ open_positions (current holdings)
│  ├─ market_data (price history)
│  └─ position_history (closed positions)
│
├─ Analysis Data
│  ├─ recommendations (AI suggestions)
│  ├─ news_items (articles with sentiment)
│  ├─ market_indicators (cached calculations)
│  └─ geopolitical_events
│
├─ Notification & Audit
│  ├─ alerts (sent notifications)
│  ├─ alert_logs (delivery tracking)
│  ├─ claude_usage (API calls & cost)
│  └─ bot_runs (execution logs)
│
├─ Caching Layer (Redis)
│  ├─ market:SPY:price (5 min TTL)
│  ├─ sentiment:market (hourly)
│  ├─ cache:technical:symbols (hourly)
│  └─ session:user_id (24 hour)
│
└─ Queue (Bull - Redis backed)
   ├─ analysis_jobs
   ├─ notification_jobs
   └─ claude_api_calls
```

---

## 4. DEPLOYMENT ARCHITECTURE

### 4.1 Local Development (Docker Compose)

```
docker-compose up

┌──────────────────────────────────────────────────┐
│ Development Environment                          │
├──────────────────────────────────────────────────┤
│                                                  │
│  Frontend: http://localhost:3001                │
│  API:      http://localhost:3000                │
│  Database: postgresql://localhost:5432          │
│  Cache:    redis://localhost:6379               │
│                                                  │
│  Services:                                       │
│  ├─ api (Node.js Express)                       │
│  ├─ bot (Python)                                │
│  ├─ postgres (Database)                         │
│  ├─ redis (Cache)                               │
│  └─ frontend (React dev server)                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 4.2 Production Deployment (AWS)

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Cloud Architecture                    │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    CDN & Static Assets                       │
│  AWS CloudFront + S3 (React SPA build artifacts)            │
│  - Global edge locations                                    │
│  - Caching strategy for static files                        │
│  - Custom domain with SSL                                  │
└──────────────┬───────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────┐
│                    Load Balancer                             │
│  AWS Application Load Balancer (ALB)                        │
│  - SSL/TLS termination                                      │
│  - Route /api to API service                                │
│  - Route /ws to WebSocket service                           │
│  - Health checks                                            │
│  - Auto-scaling triggers                                    │
└──────────────┬──────────────────────────────────────────────┘
               │
   ┌───────────┼──────────────┬─────────────────┐
   │           │              │                 │
   ▼           ▼              ▼                 ▼
┌─────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│API Pod 1│ │API Pod │ │API Pod N │ │Bot Worker│
│(Fargate)│ │(Fargate)│ │(Fargate) │ │(ECS Task)│
└─────────┘ └────────┘ └──────────┘ └──────────┘

All connected to:
┌────────────────┐  ┌─────────────┐  ┌──────────────┐
│ RDS PostgreSQL │  │ElastiCache  │  │CloudWatch    │
│ Multi-AZ       │  │Redis        │  │Logs/Metrics  │
│ Backups        │  │Cluster      │  │              │
└────────────────┘  └─────────────┘  └──────────────┘

Secrets Management:
┌─────────────────────────────────────┐
│ AWS Secrets Manager                 │
│ ├─ Broker API keys (encrypted)      │
│ ├─ Claude API key                   │
│ ├─ Database password                │
│ ├─ Slack webhook URL                │
│ └─ Service-to-service tokens        │
└─────────────────────────────────────┘

CI/CD Pipeline:
GitHub → GitHub Actions → ECR → ECS (auto-deploy)
   ↓
   • Build Docker images
   • Run tests
   • Push to ECR
   • Update ECS services
   • Zero-downtime deployment
```

### 4.3 Scaling Strategy

```
Horizontal Scaling (Phase 2+)

Current Load (Phase 1):
├─ 1 API instance (Fargate)
├─ 1 Bot worker (ECS)
├─ 1 PostgreSQL instance
└─ 1 Redis cluster

Growing Load (Phase 2):
├─ 3 API instances (auto-scale)
├─ 2 Bot workers (parallel analysis)
├─ RDS with read replicas
└─ Redis cluster (sharded)

Heavy Load (Phase 3):
├─ 10+ API instances (auto-scale)
├─ 5+ Bot workers (distributed)
├─ Database sharding by user_id
└─ Redis cluster (multi-region)

Auto-scaling Rules:
├─ Scale up: CPU > 70% or Memory > 80%
├─ Scale down: CPU < 30% for 10 minutes
├─ Min instances: 2 (high availability)
└─ Max instances: 10 (cost limit)
```

---

## 5. TECHNOLOGY STACK RATIONALE

### 5.1 Why These Technologies?

| Component | Technology | Alternatives | Why Chosen |
|-----------|-----------|--------------|-----------|
| **API Server** | Node.js 18 + Express 4 | Go (Gin), Python (FastAPI), Java (Spring) | Non-blocking I/O, WebSocket support, JSON-native, team familiarity |
| **Bot Engine** | Python 3.11 | Go, Rust, Node.js | Superior data science libraries (pandas, numpy, ta), ML-ready, analysis logic clarity |
| **Database** | PostgreSQL 15 | MySQL, MongoDB, DynamoDB | ACID compliance, relational data, full-text search, JSON support, financial safety |
| **Cache/Queue** | Redis 7 | Memcached, RabbitMQ | Pub/sub for real-time, task queue, simple setup, great performance |
| **Frontend** | React 18 | Vue 3, Angular, Svelte | Component ecosystem, real-time libraries, team skills, Recharts for finance charts |
| **State** | Zustand | Redux, Jotai, Recoil | Lightweight, easy to learn, sufficient for this scale, minimal boilerplate |
| **Deployment** | Docker + AWS ECS | Kubernetes, Heroku, Digital Ocean | Docker standardization, AWS ecosystem, managed service, cost-effective |
| **CI/CD** | GitHub Actions | GitLab, Jenkins, CircleCI | Free with GitHub, good documentation, fast feedback, native to workflow |
| **Monitoring** | CloudWatch + DataDog | New Relic, Prometheus, Grafana | CloudWatch: AWS native, DataDog: better dashboard, combined = comprehensive |
| **AI** | Claude Haiku | GPT-4, LLaMA, Cohere | Cost-optimized, best for financial analysis, multi-turn conversations, fast |

### 5.2 Comparison with Alternatives

```
MONOLITHIC vs. MICROSERVICES:

Monolithic (Single service):
├─ Pros: Simpler to start, single deployment
├─ Cons: Can't scale parts independently, harder to maintain
└─ Best for: <100k users

✅ MICROSERVICES (Chosen):
├─ Pros: Scale each part independently, easier testing, faster deployments
├─ Cons: More complex setup, needs good DevOps
└─ Best for: 100k+ users, complex systems

SERVERLESS vs. CONTAINERS:

Serverless (Lambda):
├─ Pros: No server management, pay per execution
├─ Cons: Cold starts (10+ seconds), can't handle long-running bot
└─ Not suitable: Bot needs to run scheduled jobs

✅ CONTAINERS (Chosen):
├─ Pros: Consistent environment, predictable performance, long-running jobs
├─ Cons: Need to manage infrastructure
└─ Best for: Trading bots, scheduled analysis

MONOLITH DB vs. POLYDATABASE:

Monolith DB:
├─ PostgreSQL only
├─ Pros: Single source of truth
└─ Cons: Not optimal for all use cases

✅ HYBRID (Chosen):
├─ PostgreSQL (relational data)
├─ Redis (real-time, caching, queues)
└─ S3 (logs, backups, large files)
```

---

## 6. DATA FLOW ARCHITECTURE

### 6.1 Real-time Market Analysis Flow

```
Every 4 Hours (Smart Trigger Decision)
│
├─ STEP 1: Data Collection (Parallel)
│  ├─ Market prices from Yahoo Finance
│  ├─ News from multiple feeds
│  ├─ Broker positions from Alpaca/IB
│  └─ Store in PostgreSQL
│
├─ STEP 2: Quick Analysis (No AI cost)
│  ├─ Technical indicators (MA, RSI, MACD)
│  ├─ Sentiment scoring (VADER on news)
│  ├─ Geopolitical event detection
│  ├─ Volatility calculation
│  └─ Cache results in Redis
│
├─ STEP 3: AI Trigger Decision
│  Decision tree:
│  ├─ IF volatility > 25% → Use Claude (HIGH_VOL)
│  ├─ ELIF sentiment flipped → Use Claude (SENT_FLIP)
│  ├─ ELIF geopolitical event → Use Claude (GEO_EVENT)
│  ├─ ELIF major technical signal → Use Claude (TECH_SIGNAL)
│  ├─ ELIF Friday EOD → Use Claude (WEEKLY)
│  └─ ELSE → Skip Claude (NORMAL)
│
├─ STEP 4: Claude Analysis (If triggered)
│  Turn 1: "Analyze this market data"
│  ├─ Receives: prices, technical, sentiment, geo
│  └─ Returns: Initial assessment
│
│  Turn 2: "Specific risk assessment"
│  ├─ Receives: Position details, risks
│  └─ Returns: Risk analysis
│
│  Turn 3: "Generate recommendations"
│  ├─ Receives: All context
│  └─ Returns: JSON recommendations
│
├─ STEP 5: Recommendation Generation
│  ├─ Parse Claude JSON
│  ├─ Add stop loss & profit targets
│  ├─ Calculate conviction level
│  ├─ Store in PostgreSQL
│  └─ Track Claude API cost
│
├─ STEP 6: Alert Dispatch
│  ├─ Send to Slack (detailed)
│  ├─ Send to Email (formatted)
│  ├─ Send to SMS (brief)
│  ├─ Push to Dashboard (real-time)
│  └─ Store alert log
│
└─ STEP 7: Monitoring
   ├─ Log execution time
   ├─ Track Claude cost
   ├─ Monitor alert delivery
   └─ Store bot run record

Database writes:
├─ market_data table (prices, indicators)
├─ news_items table (articles)
├─ recommendations table (AI suggestions)
├─ alerts table (notifications sent)
├─ claude_usage table (API calls)
└─ bot_runs table (execution log)
```

### 6.2 Real-time Price Update Flow

```
Every 5 minutes (During market hours)
│
├─ Fetch latest prices
│  └─ Yahoo Finance API
│
├─ Update Redis cache
│  └─ market:symbol:price (5 min TTL)
│
├─ Broadcast via WebSocket
│  └─ All connected clients get update
│
└─ Store snapshot in PostgreSQL (daily)
   └─ market_data table (daily OHLCV)

WebSocket message flow:
Backend                        Frontend
   │                              │
   ├─ New price update            │
   └─ Broadcast event────────────→│
                                  ├─ Update Redux store
                                  ├─ Animate price change
                                  ├─ Update charts
                                  └─ Refresh P&L
```

### 6.3 Notification Delivery Flow

```
New Recommendation Generated
│
├─ Slack Notifier
│  ├─ Format recommendation
│  ├─ Add emoji/formatting
│  └─ POST to Slack webhook
│     └─ Immediate (< 1 sec)
│
├─ Email Notifier
│  ├─ Format HTML template
│  ├─ Queue in Bull (Redis)
│  └─ SendGrid sends within 1-5 min
│
├─ SMS Notifier (if HIGH conviction)
│  ├─ Format 160 char message
│  ├─ Queue in Bull
│  └─ Twilio sends within 30 seconds
│
├─ Dashboard Notifier
│  ├─ Push via WebSocket immediately
│  ├─ Store in alerts table
│  └─ Frontend shows toast notification
│
└─ Error Handling
   ├─ IF Slack fails → Retry 3x with exponential backoff
   ├─ IF Email fails → Queue for retry (next hour)
   ├─ IF SMS fails → Alert operator
   └─ ALL attempts logged in alert_logs table
```

---

## 7. SECURITY ARCHITECTURE

### 7.1 Authentication & Authorization

```
Login Flow:
User enters email/password
   ↓
POST /auth/login
   ↓
Verify credentials (bcrypt)
   ↓
Generate JWT token (HS256)
   ├─ user_id
   ├─ email
   ├─ roles
   └─ exp: now + 1 hour
   ↓
Return: { access_token, refresh_token, expires_in }
   ↓
Client stores tokens in memory (not localStorage)
   ↓
Every API request includes:
Authorization: Bearer <access_token>
   ↓
API verifies token & extracts user_id
   ↓
Use user_id for data isolation

Token Refresh:
Access token expires → Use refresh token
   POST /auth/refresh { refresh_token }
   ↓
Verify refresh token (in database)
   ↓
Generate new access token
   ↓
Return new token

Token Storage:
├─ Access token: Memory (cleared on logout)
├─ Refresh token: HttpOnly cookie (can't be stolen via XSS)
└─ CSRF protection: SameSite=Strict
```

### 7.2 Data Security

```
Encryption at Rest:
├─ Database: RDS encryption enabled (AES-256)
├─ Secrets: AWS Secrets Manager (encrypted)
├─ API Keys: Stored encrypted in database
└─ Backups: Encrypted snapshots

Encryption in Transit:
├─ All APIs: HTTPS only (TLS 1.2+)
├─ WebSocket: WSS (secure WebSocket)
├─ External APIs: HTTPS (Broker, Claude, Slack)
└─ Internal services: mTLS (mutual TLS)

Key Rotation:
├─ API keys: Rotated every 90 days
├─ Database password: Every 60 days
├─ JWT signing key: Every 180 days
└─ Automated alerts for approaching rotation
```

### 7.3 Access Control

```
Row-Level Security (Phase 2):
PostgreSQL RLS
├─ Users see only their own positions
├─ Users see only their own recommendations
├─ Users see only their own alerts
└─ Admin can see aggregated data (with audit)

API Rate Limiting:
├─ 100 requests/minute per user
├─ 10 requests/minute for auth endpoints
├─ 1000 requests/minute per IP (DDoS protection)
└─ Returns 429 Too Many Requests with Retry-After

Input Validation:
├─ All inputs validated (schema + type)
├─ SQL injection prevention (parameterized queries)
├─ XSS prevention (output encoding)
├─ CSRF protection (SameSite cookies)
└─ File upload restrictions (if applicable)

Audit Logging:
├─ All API calls logged (user, timestamp, endpoint)
├─ All data changes logged (for compliance)
├─ Failed login attempts tracked (brute force detection)
├─ Sensitive data access logged
└─ Logs stored in S3 with 1-year retention
```

---

## 8. MONITORING & OBSERVABILITY

### 8.1 Metrics to Track

```
Application Metrics:
├─ API response time (p50, p95, p99)
├─ Request error rate (4xx, 5xx)
├─ API availability percentage
├─ Database query performance
├─ Claude API call success rate
├─ Recommendation generation time
├─ Alert delivery latency
└─ WebSocket connection count

Business Metrics:
├─ Active recommendations count
├─ Recommendation accuracy (win rate)
├─ Average profit per recommendation
├─ Claude API cost per day
├─ User engagement (DAU, MAU)
├─ Alert delivery rate
└─ System uptime percentage

Infrastructure Metrics:
├─ EC2/ECS CPU usage
├─ Memory usage
├─ Database connections
├─ Redis memory usage
├─ Network I/O
├─ Disk space
└─ Cost per hour

Alerts (Paging):
├─ API error rate > 5% → PagerDuty
├─ Database down → Immediate
├─ Claude API failures > 20% → Slack
├─ Recommendation accuracy < 40% → Email
└─ System uptime < 99% (daily) → Review
```

### 8.2 Logging Strategy

```
Structured Logging (JSON):
{
  "timestamp": "2026-03-05T14:30:00Z",
  "level": "info",
  "service": "api",
  "request_id": "req_12345",
  "user_id": "user_abc",
  "endpoint": "POST /recommendations",
  "status": 201,
  "response_time_ms": 245,
  "message": "Recommendation created"
}

Log Destinations:
├─ CloudWatch Logs (real-time)
├─ S3 (long-term storage, 1 year)
├─ DataDog (analysis & dashboards)
└─ ELK Stack (optional, self-hosted)

Log Retention:
├─ Hot: 7 days (searchable)
├─ Warm: 30 days (searchable)
├─ Cold: 365 days (archived in S3)
└─ Purge: After 365 days
```

---

## 9. DISASTER RECOVERY & BACKUP

### 9.1 Backup Strategy

```
Database Backups:
├─ Automated daily at 2 AM UTC
├─ Automated hourly transaction logs
├─ Weekly off-site copy
├─ Point-in-time recovery (7 days)
├─ Monthly snapshots (1 year retention)
└─ Tested monthly (restore to dev environment)

Recovery Time Objectives (RTO):
├─ Full database: 15 minutes
├─ Partial data: 5 minutes
└─ Single record: <1 minute

Recovery Point Objective (RPO):
├─ Transaction logs: 1 minute
├─ Snapshots: 24 hours
└─ Off-site: 24 hours

Backup Testing:
├─ Monthly: Full restore to dev environment
├─ Verify: Data integrity check
├─ Document: Time taken, any issues
└─ Alert: If restore fails
```

### 9.2 Disaster Recovery

```
Failover Scenarios:

Scenario 1: Database Down
├─ Time to detect: <1 minute
├─ RDS Multi-AZ automatic failover: ~60 seconds
├─ Application retries: Automatic
├─ User impact: 2-minute disruption

Scenario 2: API Service Down
├─ Time to detect: <1 minute
├─ Auto-scaling launches new instance: ~2 minutes
├─ Load balancer routes to healthy instance: Immediate
├─ User impact: <30 seconds

Scenario 3: Redis Down
├─ Impact: Cache invalidation, queue delay
├─ Fallback: Query database directly (slower)
├─ Recovery: Auto-recovery, 5 minute rebuild
├─ User impact: Slower performance for 5 minutes

Scenario 4: Claude API Down
├─ Impact: Can't generate AI recommendations
├─ Fallback: Use algorithm-only recommendations
├─ Recovery: Automatic retry when Claude back
├─ User impact: Recommendations available but less detailed

Circuit Breaker Pattern:
├─ Track failures to external APIs
├─ After 5 consecutive failures: Open circuit
├─ Stop calling failing service for 60 seconds
├─ Try again after cooldown
├─ Gracefully degrade when external service fails
```

---

## 10. COST ANALYSIS

### 10.1 Infrastructure Costs (Monthly)

```
AWS Services:

Compute:
├─ ECS Fargate (API service): $150-300/month
│  └─ 2 CPU, 4GB RAM, 1 instance
├─ ECS Fargate (Bot worker): $75-150/month
│  └─ 1 CPU, 2GB RAM, 1 instance
└─ Lambda (optional): $0-50/month

Database:
├─ RDS PostgreSQL: $300-500/month
│  └─ db.t3.medium, Multi-AZ backup
└─ Backup storage: $20-50/month

Caching & Queue:
├─ ElastiCache Redis: $100-200/month
│  └─ cache.t3.small

Storage & CDN:
├─ S3 (logs, backups): $10-20/month
└─ CloudFront (CDN): $5-15/month

Networking:
├─ NAT Gateway: $32/month
├─ Load Balancer: $16/month
└─ Data transfer: $10-30/month

Monitoring & Logging:
├─ CloudWatch: $10-20/month
├─ DataDog: $200-500/month (optional)
└─ CloudTrail: $2/month

Total AWS: $1,000-$2,000/month

External APIs:
├─ Claude API: $100-200/month
├─ News APIs: $200-500/month
├─ Slack: $0 (free webhook)
├─ SendGrid (email): $100-200/month
└─ Twilio (SMS): $50-100/month

Total External: $450-$1,000/month

TOTAL MONTHLY: $1,450-$3,000/month
(Phase 1 small scale; grows with users)
```

### 10.2 Scaling Costs

```
Phase 1 (1 user):
├─ Infrastructure: $1,450/month
├─ APIs: $450/month
└─ Total: $1,900/month

Phase 2 (10 users, with SaaS revenue $100/user = $1,000):
├─ Infrastructure: $3,000/month (more instances, bigger DB)
├─ APIs: $1,000/month
└─ Total: $4,000/month
└─ Revenue: $1,000/month
└─ Net cost: $3,000/month

Phase 3 (100 users, with SaaS revenue $100/user = $10,000):
├─ Infrastructure: $8,000/month (heavy scaling)
├─ APIs: $3,000/month
└─ Total: $11,000/month
└─ Revenue: $10,000/month
└─ Net cost: $1,000/month

Phase 4 (1000 users, with SaaS revenue $100/user = $100,000):
├─ Infrastructure: $25,000/month
├─ APIs: $10,000/month
└─ Total: $35,000/month
└─ Revenue: $100,000/month
└─ Profit: $65,000/month
```

---

## 11. ALTERNATIVE ARCHITECTURES (Considered & Rejected)

### 11.1 Serverless Architecture (Rejected)

```
What it would look like:
├─ Frontend: S3 + CloudFront
├─ API: AWS Lambda + API Gateway
├─ Bot: Lambda scheduled
├─ Database: DynamoDB (NoSQL)
└─ Queue: SQS

Why Rejected:
├─ ❌ Lambda cold starts (10+ seconds) = bad UX
├─ ❌ DynamoDB costs more for relational queries
├─ ❌ Hard to run scheduled analysis jobs reliably
├─ ❌ No persistent connections (WebSocket is hard)
├─ ⚠️ Vendor lock-in (harder to migrate)

Better for: Simple CRUD apps, sporadic traffic
Not suitable: Trading bots, real-time analysis
```

### 11.2 Monolithic Architecture (Rejected)

```
What it would look like:
├─ Single Node.js service (API + Bot + Analysis)
├─ Single Docker container
├─ All logic in one codebase
└─ PostgreSQL database

Why Rejected:
├─ ❌ Can't scale analysis without scaling API
├─ ❌ Can't deploy just bot changes without API downtime
├─ ❌ Harder to test individual components
├─ ❌ Single point of failure
├─ ⚠️ Code becomes harder to maintain (monolith problem)

Better for: <1000 users, simple systems
Not suitable: 100k+ users, complex analysis
```

### 11.3 Kubernetes Architecture (Not for Phase 1)

```
What it would look like:
├─ Kubernetes cluster (self-managed or EKS)
├─ Docker containers in Pods
├─ Service mesh (Istio)
├─ Helm for deployment
└─ More complex setup

Why not Phase 1:
├─ ❌ Overkill complexity for 1 user
├─ ❌ Learning curve steep
├─ ❌ Setup time: 2-3 weeks
├─ ❌ Operational overhead

Better for: Phase 3 (1000+ users)
Phase 1-2: ECS Fargate simpler & faster
```

---

## 12. ARCHITECTURE DECISION RECORDS (ADRs)

### ADR-001: Node.js for API vs. Python for everything

**Decision:** Use Node.js for API, Python for Bot

**Rationale:**
- Python has superior data science libraries
- Node.js better for real-time APIs (WebSocket, async)
- Separation of concerns improves maintainability

**Trade-offs:**
- Two languages = more complex DevOps
- But: Better performance per language

**Status:** ✅ APPROVED

---

### ADR-002: PostgreSQL for everything vs. Polyglot databases

**Decision:** PostgreSQL + Redis + S3 (Polyglot)

**Rationale:**
- PostgreSQL for relational, transactional data
- Redis for caching & real-time queue
- S3 for logs & backup storage
- Each technology optimized for its use case

**Trade-offs:**
- More databases to manage
- But: Better performance overall

**Status:** ✅ APPROVED

---

### ADR-003: Microservices vs. Monolith

**Decision:** Microservices (API + Bot + Services)

**Rationale:**
- Independent scaling
- Independent deployment
- Easier testing
- Future-proof for SaaS

**Trade-offs:**
- More complex initially
- But: Easier to maintain long-term

**Status:** ✅ APPROVED

---

### ADR-004: AWS ECS Fargate vs. Kubernetes

**Decision:** ECS Fargate for Phase 1-2, Kubernetes for Phase 3+

**Rationale:**
- ECS: Simpler setup, managed by AWS
- Kubernetes: Better for very large scale

**Trade-offs:**
- ECS migration to K8s later if needed
- But: Faster initial time-to-market

**Status:** ✅ APPROVED

---

## 13. IMPLEMENTATION ROADMAP

### Phase 1 (Weeks 1-5): Local Development

```
├─ Week 1: Setup & Foundation
│  ├─ Docker Compose configuration
│  ├─ Database schema creation
│  ├─ API scaffolding (Express)
│  └─ Bot scaffolding (Python)
│
├─ Week 2: Data Pipeline
│  ├─ Market data collection
│  ├─ Broker API integration
│  └─ Analysis modules
│
├─ Week 3: AI Integration
│  ├─ Claude API integration
│  ├─ Recommendation engine
│  └─ Smart trigger logic
│
├─ Week 4: Alerts & UI
│  ├─ Multi-channel notifications
│  ├─ React dashboard
│  └─ WebSocket real-time
│
└─ Week 5: Testing & Optimization
   ├─ Unit tests (80%+ coverage)
   ├─ Integration tests
   ├─ Performance optimization
   └─ 48-hour test run
```

### Phase 2 (Weeks 6-9): Multi-user & Production

```
├─ Week 6: User Management
│  ├─ Authentication (JWT)
│  ├─ Multi-user support
│  └─ Authorization
│
├─ Week 7: Multi-broker & Deployment
│  ├─ Interactive Brokers integration
│  ├─ AWS infrastructure setup
│  └─ CI/CD pipeline
│
├─ Week 8: Production Deployment
│  ├─ Deploy to AWS
│  ├─ Monitoring setup
│  └─ Security hardening
│
└─ Week 9: Beta Launch
   ├─ Invite beta testers
   ├─ Collect feedback
   └─ Iterate & improve
```

### Phase 3 (Weeks 10+): Scale & Monetize

```
├─ Weeks 10-12: Mobile App
├─ Weeks 13-14: Advanced Features
├─ Weeks 15-18: Scale Infrastructure
└─ Week 18+: Public Launch
```

---

## 14. RISK MITIGATION

### Technical Risks

```
Risk 1: Claude API cost overrun
├─ Mitigation: Smart trigger logic (70% reduction)
├─ Monitoring: Track cost daily
└─ Circuit breaker: Stop using if over budget

Risk 2: Database performance degradation
├─ Mitigation: Proper indexing from day 1
├─ Monitoring: Query performance logs
└─ Scaling: Read replicas when needed

Risk 3: WebSocket connection management
├─ Mitigation: Graceful disconnect handling
├─ Monitoring: Connection count tracking
└─ Testing: Load testing before production

Risk 4: Broker API reliability
├─ Mitigation: Fallback brokers, caching
├─ Monitoring: Broker uptime tracking
└─ Circuit breaker: Graceful degradation
```

---

## 15. CONCLUSION

### Proposed Solution Summary

This **Microservices Architecture** provides:

✅ **Scalability:** Each component scales independently  
✅ **Reliability:** Multiple components, fault tolerance  
✅ **Maintainability:** Clear separation of concerns  
✅ **Performance:** Technology optimized per use case  
✅ **Cost-effective:** Efficient resource usage  
✅ **Future-proof:** Easy to add features/brokers  
✅ **Production-ready:** Security, monitoring, backups  

### Next Steps

1. ✅ **Approve this architecture**
2. ✅ **Review the complete roadmap** (provided)
3. ✅ **Assemble team** (7-9 people)
4. ✅ **Setup development environment** (Docker)
5. ✅ **Start Sprint 1** (Foundation)

---

**Architecture Status:** ✅ READY FOR IMPLEMENTATION

**Architecture Complexity:** Medium (Microservices)  
**Learning Curve:** Moderate (2-3 weeks to full understanding)  
**Scalability:** Excellent (1 → 1,000,000+ users)  
**Cost:** Reasonable ($1,900-$4,000/month Phase 1-2)
