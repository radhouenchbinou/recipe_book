"""Market data collector — fetches daily OHLCV from Yahoo Finance.

Task S1-T2-001
"""

from datetime import date, timedelta
from typing import Optional
import structlog
import yfinance as yf

from config import TRACKED_SYMBOLS
from db import get_session

log = structlog.get_logger()

_UPSERT_SQL = """
INSERT INTO market_data (symbol_id, trade_date, open, high, low, close, volume)
SELECT s.id, :trade_date, :open, :high, :low, :close, :volume
FROM   symbols s
WHERE  s.ticker = :ticker
ON CONFLICT (symbol_id, trade_date) DO UPDATE
    SET open   = EXCLUDED.open,
        high   = EXCLUDED.high,
        low    = EXCLUDED.low,
        close  = EXCLUDED.close,
        volume = EXCLUDED.volume
"""


def fetch_symbol(
    ticker: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> int:
    """Fetch OHLCV for *ticker* and persist to DB. Returns number of rows upserted."""
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=5)  # default: last 5 calendar days

    log.info("market_data.fetch", ticker=ticker, start=str(start), end=str(end))

    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),  # yfinance end is exclusive
        auto_adjust=True,
        progress=False,
    )

    if df.empty:
        log.warning("market_data.empty", ticker=ticker)
        return 0

    session = get_session()
    count = 0
    try:
        from sqlalchemy import text
        for ts, row in df.iterrows():
            session.execute(
                text(_UPSERT_SQL),
                {
                    "ticker": ticker,
                    "trade_date": ts.date(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                },
            )
            count += 1
        session.commit()
    except Exception as exc:
        session.rollback()
        log.error("market_data.db_error", ticker=ticker, error=str(exc))
        raise
    finally:
        session.close()

    log.info("market_data.saved", ticker=ticker, rows=count)
    return count


def fetch_all_symbols() -> dict[str, int]:
    """Fetch market data for all tracked symbols. Returns {ticker: rows_saved}."""
    results: dict[str, int] = {}
    for ticker in TRACKED_SYMBOLS:
        try:
            results[ticker] = fetch_symbol(ticker)
        except Exception as exc:
            log.error("market_data.fetch_failed", ticker=ticker, error=str(exc))
            results[ticker] = 0
    return results
