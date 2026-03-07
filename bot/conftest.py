"""
pytest conftest — stub out heavy / environment-dependent modules so tests run
without a live database, broker credentials, or ML models installed.
"""
import sys
import types
from unittest.mock import MagicMock

# ── Stub: pandas (required by alpaca_trade_api.entity) ─────────────────────
pandas_stub = types.ModuleType("pandas")
pandas_stub.DataFrame = MagicMock
pandas_stub.Series    = MagicMock
sys.modules.setdefault("pandas", pandas_stub)

# ── Stub: alpaca_trade_api ──────────────────────────────────────────────────
_alpaca_pkg = types.ModuleType("alpaca_trade_api")
_alpaca_rest = types.ModuleType("alpaca_trade_api.rest")
_alpaca_rest.REST = MagicMock
_alpaca_pkg.REST  = MagicMock
sys.modules.setdefault("alpaca_trade_api",      _alpaca_pkg)
sys.modules.setdefault("alpaca_trade_api.rest",  _alpaca_rest)

# ── Stub: transformers / torch (FinBERT sentiment) ─────────────────────────
for mod in ("transformers", "torch", "torch.nn", "torch.nn.functional"):
    sys.modules.setdefault(mod, types.ModuleType(mod))

# ── Stub: yfinance ──────────────────────────────────────────────────────────
yf_stub = types.ModuleType("yfinance")
yf_stub.download = MagicMock(return_value=MagicMock())
sys.modules.setdefault("yfinance", yf_stub)

# ── Stub: feedparser ────────────────────────────────────────────────────────
fp_stub = types.ModuleType("feedparser")
fp_stub.parse = MagicMock(return_value={"entries": []})
sys.modules.setdefault("feedparser", fp_stub)

# ── Stub: psycopg2 (PostgreSQL adapter — not available in test environment) ─
psycopg2_stub = types.ModuleType("psycopg2")
psycopg2_stub.connect = MagicMock()
psycopg2_stub.extensions = types.ModuleType("psycopg2.extensions")
sys.modules.setdefault("psycopg2",            psycopg2_stub)
sys.modules.setdefault("psycopg2.extensions", psycopg2_stub.extensions)

# ── Stub: db.get_session (prevents SA engine creation at import time) ───────
_db_stub = types.ModuleType("db")
_db_stub.get_session = MagicMock(return_value=MagicMock())
sys.modules.setdefault("db", _db_stub)

# ── Environment variables (prevents KeyError in config.py) ─────────────────
import os
os.environ.setdefault("DATABASE_URL",        "postgresql://test:test@localhost/test")
os.environ.setdefault("ALPACA_API_KEY",      "test-key")
os.environ.setdefault("ALPACA_SECRET_KEY",   "test-secret")
os.environ.setdefault("ALPACA_BASE_URL",     "https://paper-api.alpaca.markets")
os.environ.setdefault("ANTHROPIC_API_KEY",   "test-anthropic-key")
os.environ.setdefault("REDIS_URL",           "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET",          "test-secret")
