"""Tests for bot/portfolio/optimizer.py — Phase 2 Sprint 3"""

import pytest
from unittest.mock import patch, MagicMock

from portfolio.optimizer import PortfolioOptimizer, OptimizationResult, OptimizedWeight


# ── Helpers ────────────────────────────────────────────────────────────────

def _optimizer(**kwargs) -> PortfolioOptimizer:
    return PortfolioOptimizer(
        vol_penalty=kwargs.get("vol_penalty", 2.0),
        invested_pct=kwargs.get("invested_pct", 0.80),
        max_weight=kwargs.get("max_weight", 0.25),
        min_weight=kwargs.get("min_weight", 0.02),
        min_score=kwargs.get("min_score", 50.0),
        lookback_days=kwargs.get("lookback_days", 30),
    )


def _score_rows(data: list[tuple]) -> list:
    """Create mocked DB rows: (ticker, composite_score)."""
    rows = []
    for ticker, score in data:
        row = MagicMock()
        row.__getitem__ = lambda self, i: (ticker, score)[i]
        rows.append((ticker, score))
    return rows


def _mock_session_for_scores(scores, price_rows=None):
    session = MagicMock()
    score_result = MagicMock()
    score_result.fetchall.return_value = [(t, s) for t, s in scores]
    price_result = MagicMock()
    price_result.fetchall.return_value = price_rows or []
    session.execute.side_effect = [score_result, price_result]
    return session


# ── PortfolioOptimizer.optimize ─────────────────────────────────────────────

class TestOptimizerOptimize:
    @patch("portfolio.optimizer.get_session")
    def test_returns_optimization_result(self, mock_get):
        mock_get.return_value = _mock_session_for_scores(
            [("AAPL", 70), ("MSFT", 65), ("SPY", 60)]
        )
        result = _optimizer().optimize()
        assert isinstance(result, OptimizationResult)
        assert len(result.weights) > 0

    @patch("portfolio.optimizer.get_session")
    def test_all_bearish_returns_empty(self, mock_get):
        mock_get.return_value = _mock_session_for_scores(
            [("AAPL", 40), ("MSFT", 30)]
        )
        result = _optimizer().optimize()
        assert result.weights == []
        assert "No bullish" in result.notes or "zero" in result.notes.lower()

    @patch("portfolio.optimizer.get_session")
    def test_total_invested_leq_invested_pct(self, mock_get):
        mock_get.return_value = _mock_session_for_scores(
            [("AAPL", 75), ("MSFT", 70), ("SPY", 65), ("QQQ", 60), ("GLD", 55), ("NVDA", 80)]
        )
        result = _optimizer(invested_pct=0.80).optimize()
        assert result.total_invested_pct <= 0.80 + 0.001   # small float tolerance

    @patch("portfolio.optimizer.get_session")
    def test_no_weight_exceeds_max(self, mock_get):
        mock_get.return_value = _mock_session_for_scores(
            [("AAPL", 90)]   # single symbol
        )
        result = _optimizer(max_weight=0.25).optimize()
        for w in result.weights:
            assert w.final_weight <= 0.25 + 0.001

    @patch("portfolio.optimizer.get_session")
    def test_higher_vol_reduces_weight(self, mock_get):
        """Two symbols with same score but different vols — higher vol gets less weight."""
        # Provide prices that give NVDA higher volatility
        import datetime
        today = datetime.date.today()
        nvda_prices = [(f"NVDA", 100 + (i % 5) * 10, today) for i in range(20)]   # high vol
        spy_prices  = [(f"SPY",  400 + i * 0.1,       today) for i in range(20)]  # low vol

        score_result = MagicMock()
        score_result.fetchall.return_value = [("NVDA", 70.0), ("SPY", 70.0)]

        price_result = MagicMock()
        price_result.fetchall.return_value = [
            ("NVDA", 100 + (i % 5) * 10, today) for i in range(20)
        ] + [("SPY", 400 + i * 0.1, today) for i in range(20)]

        session = MagicMock()
        session.execute.side_effect = [score_result, price_result]
        mock_get.return_value = session

        result = _optimizer(vol_penalty=2.0).optimize()
        nvda_w = next((w for w in result.weights if w.ticker == "NVDA"), None)
        spy_w  = next((w for w in result.weights if w.ticker == "SPY"),  None)

        if nvda_w and spy_w:
            # NVDA is higher vol → should have lower or equal weight
            assert nvda_w.final_weight <= spy_w.final_weight + 0.01

    @patch("portfolio.optimizer.get_session")
    def test_cash_pct_equals_one_minus_invested(self, mock_get):
        mock_get.return_value = _mock_session_for_scores(
            [("AAPL", 65), ("SPY", 60)]
        )
        result = _optimizer().optimize()
        assert abs(result.total_invested_pct + result.cash_pct - 1.0) < 0.01

    @patch("portfolio.optimizer.get_session")
    def test_current_weights_change_reported(self, mock_get):
        mock_get.return_value = _mock_session_for_scores([("AAPL", 70)])
        current = {"AAPL": 0.05}
        result = _optimizer().optimize(current_weights=current)
        if result.weights:
            aapl = result.weights[0]
            assert aapl.change_from_current == pytest.approx(
                aapl.final_weight - 0.05, abs=0.001
            )


# ── PortfolioOptimizer._renormalise ─────────────────────────────────────────

class TestRenormalise:
    def test_renormalise_sums_to_invested_pct(self):
        weights = {"AAPL": 0.30, "MSFT": 0.20, "SPY": 0.15}
        result = PortfolioOptimizer._renormalise(weights)
        assert abs(sum(result.values()) - 0.80) < 0.001

    def test_renormalise_empty_dict(self):
        result = PortfolioOptimizer._renormalise({})
        assert result == {}

    def test_renormalise_preserves_proportions(self):
        weights = {"A": 1.0, "B": 1.0}
        result = PortfolioOptimizer._renormalise(weights)
        assert abs(result["A"] - result["B"]) < 0.001
