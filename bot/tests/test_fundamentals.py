"""Tests for FundamentalAnalyzer."""

from unittest.mock import MagicMock, patch
import pytest
from analysis.fundamentals import FundamentalAnalyzer, FundamentalScore


MOCK_INFO_FULL = {
    "trailingPE": 20.0,           # reasonable P/E → mid score
    "earningsQuarterlyGrowth": 0.15,   # 15% EPS growth → bullish
    "revenueGrowth": 0.10,        # 10% rev growth → bullish
    "debtToEquity": 50.0,         # 0.5x (IB returns ×100)
    "returnOnEquity": 0.22,       # 22% ROE → excellent
}

MOCK_INFO_EMPTY = {}


class TestFundamentalAnalyzer:
    def test_full_data_returns_score(self):
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = MOCK_INFO_FULL
            analyzer = FundamentalAnalyzer()
            result = analyzer.analyze("AAPL")

        assert result is not None
        assert isinstance(result, FundamentalScore)
        assert 0.0 <= result.score <= 100.0
        assert result.ticker == "AAPL"

    def test_good_fundamentals_score_above_50(self):
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = MOCK_INFO_FULL
            result = FundamentalAnalyzer().analyze("MSFT")
        assert result.score > 50.0

    def test_empty_data_returns_neutral_score(self):
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = MOCK_INFO_EMPTY
            result = FundamentalAnalyzer().analyze("GLD")
        # GLD has no fundamentals — should return neutral default
        assert result is not None
        assert result.score == 50.0

    def test_fetch_failure_returns_none(self):
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = MagicMock(side_effect=Exception("network error"))
            # We need to patch the .info attribute access to raise
            mock_ticker.return_value = MagicMock()
            mock_ticker.return_value.info = property(lambda self: (_ for _ in ()).throw(Exception("network error")))

        # Alternate approach: patch at module level
        with patch("analysis.fundamentals.yf.Ticker") as mock_yf:
            mock_yf.side_effect = Exception("network error")
            result = FundamentalAnalyzer().analyze("BAD")
        assert result is None

    def test_score_range_enforced(self):
        extreme_bullish = {
            "trailingPE": 1.0,
            "earningsQuarterlyGrowth": 2.0,
            "revenueGrowth": 2.0,
            "debtToEquity": 0.0,
            "returnOnEquity": 1.0,
        }
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = extreme_bullish
            result = FundamentalAnalyzer().analyze("TEST")
        assert result.score <= 100.0

        extreme_bearish = {
            "trailingPE": 200.0,
            "earningsQuarterlyGrowth": -1.0,
            "revenueGrowth": -1.0,
            "debtToEquity": 500.0,
            "returnOnEquity": -1.0,
        }
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = extreme_bearish
            result = FundamentalAnalyzer().analyze("TEST")
        assert result.score >= 0.0
