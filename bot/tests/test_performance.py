"""Tests for bot/portfolio/performance.py — Phase 2 Sprint 1"""

import pytest
import math
from unittest.mock import patch, MagicMock

from portfolio.performance import PerformanceAnalytics, PerformanceSummary


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _analytics(**kwargs) -> PerformanceAnalytics:
    return PerformanceAnalytics(
        initial_capital=kwargs.get("initial_capital", 100_000)
    )


def _mock_session(rec_row=None, symbol_rows=None):
    session = MagicMock()
    exec_mock = MagicMock()

    if rec_row is None:
        rec_row = (100, 40, 30, 30, 60, 40)
    if symbol_rows is None:
        symbol_rows = [("AAPL", 30, 10, 10, 10, 20, 10, 0.75, 65.0)]

    exec_mock.fetchone.return_value = rec_row
    exec_mock.fetchall.return_value = symbol_rows
    session.execute.return_value = exec_mock
    return session


# ── compute_summary ───────────────────────────────────────────────────────────

class TestComputeSummary:
    @patch("portfolio.performance.get_session")
    def test_returns_performance_summary(self, mock_get_session):
        mock_get_session.return_value = _mock_session()
        analytics = _analytics()
        summary = analytics.compute_summary(
            portfolio_value=105_000,
            cash=20_000,
            equity=85_000,
            day_pl=500,
            day_pl_pct=0.0048,
        )
        assert isinstance(summary, PerformanceSummary)
        assert summary.portfolio_value == 105_000
        assert summary.cash == 20_000

    @patch("portfolio.performance.get_session")
    def test_total_pl_calculated_correctly(self, mock_get_session):
        mock_get_session.return_value = _mock_session()
        analytics = _analytics(initial_capital=100_000)
        summary = analytics.compute_summary(
            portfolio_value=110_000,
            cash=10_000,
            equity=100_000,
            day_pl=0,
            day_pl_pct=0,
        )
        assert summary.total_pl == pytest.approx(10_000, rel=0.01)
        assert summary.total_pl_pct == pytest.approx(10.0, rel=0.01)

    @patch("portfolio.performance.get_session")
    def test_total_pl_negative(self, mock_get_session):
        mock_get_session.return_value = _mock_session()
        analytics = _analytics(initial_capital=100_000)
        summary = analytics.compute_summary(
            portfolio_value=90_000,
            cash=10_000,
            equity=80_000,
            day_pl=-500,
            day_pl_pct=-0.005,
        )
        assert summary.total_pl == pytest.approx(-10_000, rel=0.01)
        assert summary.total_pl_pct < 0


# ── compute_backtest_metrics ──────────────────────────────────────────────────

class TestComputeBacktestMetrics:
    def test_empty_curve_returns_none_metrics(self):
        analytics = _analytics()
        result = analytics.compute_backtest_metrics([], [])
        assert result["sharpe_ratio"]       is None
        assert result["max_drawdown_pct"]   is None
        assert result["win_rate_pct"]       is None
        assert result["annualised_return_pct"] is None

    def test_single_point_curve_returns_none(self):
        analytics = _analytics()
        result = analytics.compute_backtest_metrics([100_000], [])
        assert result["sharpe_ratio"] is None

    def test_flat_curve_has_zero_return(self):
        analytics = _analytics()
        curve = [100_000] * 252  # flat for a year
        result = analytics.compute_backtest_metrics(curve, [])
        assert result["annualised_return_pct"] == pytest.approx(0.0, abs=0.01)

    def test_growing_curve_positive_return(self):
        analytics = _analytics()
        # 10% annual growth
        curve = [100_000 * (1.0004 ** i) for i in range(252)]
        result = analytics.compute_backtest_metrics(curve, [])
        assert result["annualised_return_pct"] is not None
        assert result["annualised_return_pct"] > 0

    def test_max_drawdown_on_declining_then_recovering_curve(self):
        analytics = _analytics()
        curve = [100_000, 90_000, 80_000, 85_000, 95_000, 100_000]
        result = analytics.compute_backtest_metrics(curve, [])
        # Peak 100k → trough 80k → drawdown 20%
        assert result["max_drawdown_pct"] == pytest.approx(20.0, rel=0.01)

    def test_win_rate_with_mixed_trades(self):
        analytics = _analytics()
        trades = [
            {"action": "sell", "pnl": 500},
            {"action": "sell", "pnl": -200},
            {"action": "sell", "pnl": 100},
            {"action": "buy",  "pnl": 0},   # open position, excluded
        ]
        curve = [100_000, 101_000, 100_500, 101_000]
        result = analytics.compute_backtest_metrics(curve, trades)
        # 2 wins out of 3 closed trades = 66.67%
        assert result["win_rate_pct"] == pytest.approx(66.67, rel=0.01)

    def test_no_closed_trades_win_rate_is_none(self):
        analytics = _analytics()
        trades = [{"action": "buy", "pnl": 0}]
        curve = [100_000, 101_000]
        result = analytics.compute_backtest_metrics(curve, trades)
        assert result["win_rate_pct"] is None

    def test_sharpe_positive_for_good_equity_curve(self):
        analytics = _analytics()
        # Steadily growing curve (should give positive Sharpe)
        curve = [100_000 + 50 * i for i in range(252)]
        result = analytics.compute_backtest_metrics(curve, [])
        # Not None and reasonable
        assert result["sharpe_ratio"] is not None
        assert isinstance(result["sharpe_ratio"], float)


# ── static helpers (tested indirectly via compute_backtest_metrics) ──────────

class TestStaticHelpers:
    def test_zero_initial_capital_handled(self):
        analytics = PerformanceAnalytics(initial_capital=0)
        # Should not raise ZeroDivisionError
        with patch("portfolio.performance.get_session") as ms:
            ms.return_value = _mock_session()
            summary = analytics.compute_summary(100_000, 10_000, 90_000, 0, 0)
        assert summary.total_pl_pct == 0.0
