"""Technical indicators module — RSI, MACD, Bollinger Bands, SMA, EMA.

Task S2-T1-001
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()


@dataclass
class IndicatorSnapshot:
    ticker: str
    close: float
    sma_20: Optional[float]
    sma_50: Optional[float]
    ema_12: Optional[float]
    ema_26: Optional[float]
    rsi_14: Optional[float]
    macd: Optional[float]
    macd_signal: Optional[float]
    macd_hist: Optional[float]
    bb_upper: Optional[float]
    bb_middle: Optional[float]
    bb_lower: Optional[float]
    bb_pct_b: Optional[float]   # position within bands: 0 = lower, 1 = upper
    technical_score: float       # 0–100 composite


# ── Raw indicator calculations ─────────────────────────────────────────────

def compute_sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower, %B)."""
    middle = compute_sma(series, window)
    std = series.rolling(window=window, min_periods=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    pct_b = (series - lower) / (upper - lower).replace(0, np.nan)
    return upper, middle, lower, pct_b


# ── Score calculation ──────────────────────────────────────────────────────

def _rsi_score(rsi: Optional[float]) -> float:
    """Map RSI to a 0–100 directional score (50 = neutral)."""
    if rsi is None:
        return 50.0
    if rsi < 30:
        return 80.0  # oversold → bullish signal
    if rsi > 70:
        return 20.0  # overbought → bearish signal
    # linear mapping: 30→80, 50→50, 70→20
    return 80.0 - (rsi - 30) * (60.0 / 40.0)


def _macd_score(macd: Optional[float], hist: Optional[float]) -> float:
    """Bullish if MACD > 0 and histogram > 0, bearish otherwise."""
    if macd is None or hist is None:
        return 50.0
    score = 50.0
    if macd > 0:
        score += 20.0
    else:
        score -= 20.0
    if hist > 0:
        score += 15.0
    else:
        score -= 15.0
    return max(0.0, min(100.0, score))


def _bb_score(pct_b: Optional[float]) -> float:
    """Map %B to a directional score (low %B = oversold = bullish)."""
    if pct_b is None:
        return 50.0
    if pct_b < 0:
        return 80.0
    if pct_b > 1:
        return 20.0
    return 80.0 - pct_b * 60.0


def compute_technical_score(snapshot: IndicatorSnapshot) -> float:
    """Weighted composite of RSI, MACD, and Bollinger Band signals (0–100)."""
    rsi_s = _rsi_score(snapshot.rsi_14)
    macd_s = _macd_score(snapshot.macd, snapshot.macd_hist)
    bb_s = _bb_score(snapshot.bb_pct_b)
    return round(0.40 * rsi_s + 0.35 * macd_s + 0.25 * bb_s, 2)


# ── Main entry point ───────────────────────────────────────────────────────

def compute_indicators(ticker: str, lookback_days: int = 60) -> Optional[IndicatorSnapshot]:
    """Load recent market data for *ticker* and compute all indicators."""
    session = get_session()
    try:
        rows = session.execute(
            text("""
                SELECT md.trade_date, md.close
                FROM   market_data md
                JOIN   symbols s ON s.id = md.symbol_id
                WHERE  s.ticker = :ticker
                ORDER  BY md.trade_date DESC
                LIMIT  :limit
            """),
            {"ticker": ticker, "limit": lookback_days},
        ).fetchall()
    finally:
        session.close()

    if not rows:
        log.warning("indicators.no_data", ticker=ticker)
        return None

    df = pd.DataFrame(rows, columns=["trade_date", "close"])
    df = df.sort_values("trade_date").reset_index(drop=True)
    closes = df["close"].astype(float)

    sma20 = compute_sma(closes, 20)
    sma50 = compute_sma(closes, 50)
    ema12 = compute_ema(closes, 12)
    ema26 = compute_ema(closes, 26)
    rsi = compute_rsi(closes)
    macd_line, signal_line, histogram = compute_macd(closes)
    bb_upper, bb_mid, bb_lower, pct_b = compute_bollinger(closes)

    def last(s: pd.Series) -> Optional[float]:
        v = s.iloc[-1]
        return None if pd.isna(v) else round(float(v), 4)

    snap = IndicatorSnapshot(
        ticker=ticker,
        close=round(float(closes.iloc[-1]), 4),
        sma_20=last(sma20),
        sma_50=last(sma50),
        ema_12=last(ema12),
        ema_26=last(ema26),
        rsi_14=last(rsi),
        macd=last(macd_line),
        macd_signal=last(signal_line),
        macd_hist=last(histogram),
        bb_upper=last(bb_upper),
        bb_middle=last(bb_mid),
        bb_lower=last(bb_lower),
        bb_pct_b=last(pct_b),
        technical_score=0.0,
    )
    snap.technical_score = compute_technical_score(snap)
    log.info("indicators.computed", ticker=ticker, score=snap.technical_score)
    return snap
