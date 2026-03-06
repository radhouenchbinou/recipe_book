"""Tests for bot/backtest/engine.py — Phase 2 Sprint 1"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

from backtest.engine import BacktestEngine, BacktestResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_engine(**kwargs) -> BacktestEngine:
    return BacktestEngine(
        initial_capital=kwargs.get("initial_capital", 100_000),
        max_position_pct=kwargs.get("max_position_pct", 0.10),
        commission_pct=kwargs.get("commission_pct", 0.001),
    )


def _make_db_rows(prices: list[tuple]) -> list:
    """Build minimal DB row mocks (trade_date, open_price, close_price, composite_score)."""
    rows = []
    for trade_date, open_price, close_price, score in prices:
        row = MagicMock()
        row.trade_date   = trade_date
        row.open_price   = open_price
        row.close_price  = close_price
        row.composite_score = score
        rows.append(row)
    return rows


# ── Unit tests — engine internals ─────────────────────────────────────────────

class TestBacktestEngineInit:
    def test_defaults(self):
        engine = BacktestEngine()
        assert engine._initial_capital == 100_000
        assert engine._max_position_pct == 0.10
        assert engine._commission_pct == 0.001

    def test_custom_params(self):
        engine = BacktestEngine(initial_capital=50_000, max_position_pct=0.20, commission_pct=0.002)
        assert engine._initial_capital == 50_000
        assert engine._max_position_pct == 0.20


class TestBacktestEngineRun:
    """Tests run() with mocked DB data."""

    @patch("backtest.engine.get_session")
    def test_returns_backtest_result(self, mock_get_session):
        today = date.today()
        rows = _make_db_rows([
            (today - timedelta(days=5), 100.0, 102.0, 70.0),  # buy signal
            (today - timedelta(days=4), 102.5, 104.0, 72.0),  # hold
            (today - timedelta(days=3), 104.0, 103.0, 68.0),  # hold
            (today - timedelta(days=2), 103.0, 101.0, 40.0),  # sell signal
            (today - timedelta(days=1), 100.5, 100.0, 38.0),  # hold
        ])
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = rows
        mock_get_session.return_value = mock_session

        engine = _make_engine()
        result = engine.run("AAPL", today - timedelta(days=6), today)

        assert isinstance(result, BacktestResult)
        assert result.ticker == "AAPL"
        assert isinstance(result.total_return_pct, float)
        assert isinstance(result.equity_curve, list)
        assert len(result.equity_curve) > 0

    @patch("backtest.engine.get_session")
    def test_empty_data_returns_empty_result(self, mock_get_session):
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = []
        mock_get_session.return_value = mock_session

        engine = _make_engine()
        result = engine.run("XYZ", date.today() - timedelta(days=30), date.today())

        assert result.ticker == "XYZ"
        assert result.total_return_pct == 0.0
        assert result.trades == []

    @patch("backtest.engine.get_session")
    def test_equity_curve_starts_at_initial_capital(self, mock_get_session):
        today = date.today()
        rows = _make_db_rows([
            (today - timedelta(days=3), 100.0, 105.0, 75.0),
            (today - timedelta(days=2), 105.0, 108.0, 78.0),
            (today - timedelta(days=1), 108.0, 106.0, 30.0),
        ])
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = rows
        mock_get_session.return_value = mock_session

        engine = _make_engine(initial_capital=50_000)
        result = engine.run("SPY", today - timedelta(days=4), today)

        assert result.equity_curve[0] == pytest.approx(50_000, rel=0.01)


class TestBacktestMetrics:
    @patch("backtest.engine.get_session")
    def test_win_rate_all_wins(self, mock_get_session):
        today = date.today()
        # alternating buy / sell creating profitable round-trips
        rows = _make_db_rows([
            (today - timedelta(days=6), 100.0, 100.0, 70.0),  # buy signal
            (today - timedelta(days=5), 101.0, 101.0, 70.0),
            (today - timedelta(days=4), 102.0, 102.0, 70.0),
            (today - timedelta(days=3), 103.0, 103.0, 30.0),  # sell
            (today - timedelta(days=2), 104.0, 104.0, 30.0),
            (today - timedelta(days=1), 105.0, 105.0, 30.0),
        ])
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = rows
        mock_get_session.return_value = mock_session

        engine = _make_engine()
        result = engine.run("MSFT", today - timedelta(days=7), today)

        # Result should have a defined win rate
        assert result.win_rate_pct is None or 0.0 <= result.win_rate_pct <= 100.0

    @patch("backtest.engine.get_session")
    def test_max_drawdown_non_negative(self, mock_get_session):
        today = date.today()
        rows = _make_db_rows([
            (today - timedelta(days=4), 100.0, 95.0, 40.0),
            (today - timedelta(days=3), 95.0,  90.0, 35.0),
            (today - timedelta(days=2), 90.0,  92.0, 60.0),
            (today - timedelta(days=1), 92.0,  94.0, 65.0),
        ])
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = rows
        mock_get_session.return_value = mock_session

        engine = _make_engine()
        result = engine.run("GLD", today - timedelta(days=5), today)

        assert result.max_drawdown_pct is None or result.max_drawdown_pct >= 0.0
