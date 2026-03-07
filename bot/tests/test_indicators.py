"""Unit tests for technical indicators.

Task S2-T1-001 acceptance criteria.
"""

import pandas as pd
import numpy as np
import pytest

from analysis.indicators import (
    compute_sma,
    compute_ema,
    compute_rsi,
    compute_macd,
    compute_bollinger,
    compute_technical_score,
    IndicatorSnapshot,
    _rsi_score,
    _macd_score,
    _bb_score,
)


@pytest.fixture()
def price_series() -> pd.Series:
    """60 days of synthetic prices with a clear upward trend."""
    np.random.seed(42)
    prices = 400.0 + np.cumsum(np.random.normal(0.5, 2.0, 60))
    return pd.Series(prices)


# ── SMA / EMA ──────────────────────────────────────────────────────────────

def test_sma_window(price_series):
    sma = compute_sma(price_series, 20)
    assert sma.iloc[:19].isna().all(), "first 19 values must be NaN"
    assert not pd.isna(sma.iloc[19])


def test_ema_no_nan_after_start(price_series):
    ema = compute_ema(price_series, 12)
    # EMA with adjust=False starts from first value
    assert not ema.iloc[11:].isna().any()


# ── RSI ────────────────────────────────────────────────────────────────────

def test_rsi_bounds(price_series):
    rsi = compute_rsi(price_series)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_rsi_score_oversold():
    assert _rsi_score(25.0) == 80.0


def test_rsi_score_overbought():
    assert _rsi_score(75.0) == 20.0


def test_rsi_score_neutral():
    score = _rsi_score(50.0)
    assert 45.0 <= score <= 55.0


# ── MACD ───────────────────────────────────────────────────────────────────

def test_macd_returns_three_series(price_series):
    macd, signal, hist = compute_macd(price_series)
    assert len(macd) == len(price_series)
    assert len(signal) == len(price_series)
    assert len(hist) == len(price_series)


def test_macd_score_bullish():
    score = _macd_score(macd=1.0, hist=0.5)
    assert score > 50.0


def test_macd_score_bearish():
    score = _macd_score(macd=-1.0, hist=-0.5)
    assert score < 50.0


# ── Bollinger Bands ────────────────────────────────────────────────────────

def test_bollinger_upper_gt_lower(price_series):
    upper, mid, lower, pct_b = compute_bollinger(price_series)
    valid = upper.dropna()
    assert (valid > lower.dropna()).all()


def test_bb_score_below_lower_band():
    assert _bb_score(-0.1) == 80.0


def test_bb_score_above_upper_band():
    assert _bb_score(1.1) == 20.0


# ── Composite score ────────────────────────────────────────────────────────

def test_compute_technical_score_range():
    snap = IndicatorSnapshot(
        ticker="SPY", close=480.0,
        sma_20=470.0, sma_50=460.0,
        ema_12=475.0, ema_26=468.0,
        rsi_14=45.0, macd=1.2, macd_signal=0.9, macd_hist=0.3,
        bb_upper=490.0, bb_middle=475.0, bb_lower=460.0, bb_pct_b=0.67,
        technical_score=0.0,
    )
    score = compute_technical_score(snap)
    assert 0.0 <= score <= 100.0


def test_technical_score_bullish_signals():
    snap = IndicatorSnapshot(
        ticker="SPY", close=480.0,
        sma_20=None, sma_50=None, ema_12=None, ema_26=None,
        rsi_14=25.0,      # oversold → bullish
        macd=2.0, macd_signal=1.0, macd_hist=1.0,  # bullish
        bb_upper=500.0, bb_middle=480.0, bb_lower=460.0, bb_pct_b=0.1,  # near lower band
        technical_score=0.0,
    )
    score = compute_technical_score(snap)
    assert score > 65.0, f"Expected bullish score > 65, got {score}"
