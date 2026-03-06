"""Central configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────
DATABASE_URL: str = os.environ["DATABASE_URL"]

# ── Redis ─────────────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Alpaca ────────────────────────────────────────────────────────────────
ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL: str = os.getenv(
    "ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
)

# ── Anthropic / Claude ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_DAILY_CALL_BUDGET: float = float(
    os.getenv("CLAUDE_DAILY_CALL_BUDGET", "0.25")
)  # fraction of daily quota (0–1)

# ── Scheduler ─────────────────────────────────────────────────────────────
MARKET_DATA_CRON: str = os.getenv("MARKET_DATA_CRON", "0 18 * * 1-5")   # 6 pm weekdays
NEWS_FETCH_CRON: str = os.getenv("NEWS_FETCH_CRON", "*/30 * * * *")      # every 30 min
ANALYSIS_CRON: str = os.getenv("ANALYSIS_CRON", "30 18 * * 1-5")        # 6:30 pm weekdays
RECOMMENDATION_CRON: str = os.getenv("RECOMMENDATION_CRON", "45 18 * * 1-5")  # 6:45 pm weekdays

# ── Symbols ───────────────────────────────────────────────────────────────
TRACKED_SYMBOLS: list[str] = os.getenv(
    "TRACKED_SYMBOLS", "SPY,QQQ,GLD,AAPL,MSFT,NVDA"
).split(",")

# ── Misc ──────────────────────────────────────────────────────────────────
BOT_ENV: str = os.getenv("BOT_ENV", "development")
HEALTH_PORT: int = int(os.getenv("HEALTH_PORT", "8080"))
