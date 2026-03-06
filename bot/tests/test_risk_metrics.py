"""Tests for bot/risk/metrics.py — Phase 2 Sprint 3"""

import pytest
import math
from unittest.mock import patch, MagicMock

from risk.metrics import RiskMetrics, PortfolioRiskReport, VaRResult, BetaResult


# ── Fixtures ────────────────────────────────────────────────────────────────

def _metrics(**kwargs) -> RiskMetrics:
    return RiskMetrics(
        confidence=kwargs.get("confidence", 0.95),
        benchmark=kwargs.get("benchmark", "SPY"),
        lookback_days=kwargs.get("lookback_days", 252),
    )


def _daily_returns_from_trend(n=252, daily_return=0.0005, noise=0.01) -> list[float]:
    """Simulate returns: steady drift + Gaussian noise."""
    import random
    random.seed(42)
    return [daily_return + random.gauss(0, noise) for _ in range(n)]


def _mock_db(returns_by_ticker: dict) -> MagicMock:
    """Build a mock session that returns prices reconstructed from returns."""
    session = MagicMock()

    all_rows = []
    for ticker, rets in returns_by_ticker.items():
        price = 100.0
        for i, r in enumerate(rets):
            all_rows.append((ticker, price, f"2024-{(i//21)+1:02d}-{(i%21)+1:02d}"))
            price *= (1 + r)

    result = MagicMock()
    result.fetchall.return_value = all_rows
    session.execute.return_value = result
    return session


# ── VaR ─────────────────────────────────────────────────────────────────────

class TestVaR:
    def test_var_is_negative(self):
        """VaR should be a negative number (loss %)."""
        m = _metrics()
        returns = _daily_returns_from_trend(252, daily_return=0.0, noise=0.02)
        result = m._compute_var("AAPL", returns)
        assert isinstance(result, VaRResult)
        assert result.var_pct < 0

    def test_cvar_leq_var(self):
        """CVaR (expected shortfall) should be worse than VaR."""
        m = _metrics()
        returns = _daily_returns_from_trend()
        result = m._compute_var("AAPL", returns)
        assert result.cvar_pct <= result.var_pct

    def test_higher_confidence_gives_worse_var(self):
        """95% VaR should be less negative than 99% VaR."""
        returns = _daily_returns_from_trend(500, noise=0.015)
        var_95 = _metrics(confidence=0.95)._compute_var("X", returns)
        var_99 = _metrics(confidence=0.99)._compute_var("X", returns)
        assert var_95.var_pct >= var_99.var_pct

    def test_zero_observations_handled(self):
        m = _metrics()
        result = m._compute_var("X", [])
        assert result.var_pct == 0.0 or result.observations == 0


# ── Beta ─────────────────────────────────────────────────────────────────────

class TestBeta:
    def test_perfect_market_beta_is_one(self):
        """Asset identical to benchmark → beta = 1.0."""
        returns = _daily_returns_from_trend(252, noise=0.01)
        result = RiskMetrics._compute_beta("X", returns, returns)
        assert result.beta == pytest.approx(1.0, abs=0.01)

    def test_uncorrelated_beta_near_zero(self):
        import random
        random.seed(99)
        asset_rets = [random.gauss(0, 0.01) for _ in range(252)]
        bench_rets = [random.gauss(0, 0.01) for _ in range(252)]
        result = RiskMetrics._compute_beta("X", asset_rets, bench_rets)
        assert abs(result.beta) < 0.4

    def test_negative_beta_when_inverse(self):
        returns = _daily_returns_from_trend(252, noise=0.0)
        inverse = [-r for r in returns]
        result = RiskMetrics._compute_beta("X", inverse, returns)
        assert result.beta < 0

    def test_correlation_between_neg1_and_1(self):
        returns = _daily_returns_from_trend(252)
        bench   = _daily_returns_from_trend(252, daily_return=0.0003)
        result  = RiskMetrics._compute_beta("X", returns, bench)
        assert -1.0 <= result.correlation <= 1.0

    def test_r_squared_between_0_and_1(self):
        returns = _daily_returns_from_trend(252)
        bench   = _daily_returns_from_trend(252)
        result  = RiskMetrics._compute_beta("X", returns, bench)
        assert 0.0 <= result.r_squared <= 1.0


# ── Correlation matrix ────────────────────────────────────────────────────────

class TestCorrelationMatrix:
    def test_diagonal_is_one(self):
        rets = {
            "AAPL": _daily_returns_from_trend(100),
            "SPY":  _daily_returns_from_trend(100, daily_return=0.0003),
        }
        corr = RiskMetrics._compute_correlation(rets, ["AAPL", "SPY"])
        assert corr.matrix["AAPL"]["AAPL"] == pytest.approx(1.0)
        assert corr.matrix["SPY"]["SPY"]   == pytest.approx(1.0)

    def test_matrix_symmetric(self):
        rets = {
            "A": _daily_returns_from_trend(100),
            "B": _daily_returns_from_trend(100, noise=0.02),
        }
        corr = RiskMetrics._compute_correlation(rets, ["A", "B"])
        assert corr.matrix["A"]["B"] == pytest.approx(corr.matrix["B"]["A"], abs=0.001)

    def test_missing_ticker_excluded(self):
        rets = {"AAPL": _daily_returns_from_trend(50)}
        corr = RiskMetrics._compute_correlation(rets, ["AAPL", "MISSING"])
        assert "MISSING" not in corr.tickers


# ── Portfolio risk integration ────────────────────────────────────────────────

class TestComputePortfolioRisk:
    @patch("risk.metrics.get_session")
    def test_returns_portfolio_risk_report(self, mock_get):
        returns = _daily_returns_from_trend(100)
        mock_get.return_value = _mock_db({"AAPL": returns, "SPY": returns})

        m = _metrics()
        report = m.compute_portfolio_risk(["AAPL"])
        assert isinstance(report, PortfolioRiskReport)

    @patch("risk.metrics.get_session")
    def test_weighted_portfolio_var_computed(self, mock_get):
        returns = _daily_returns_from_trend(100, noise=0.02)
        mock_get.return_value = _mock_db({"AAPL": returns, "SPY": returns})

        m = _metrics()
        report = m.compute_portfolio_risk(["AAPL"], weights={"AAPL": 0.50})
        assert report.portfolio_var is not None
        assert report.portfolio_cvar is not None

    @patch("risk.metrics.get_session")
    def test_empty_tickers_returns_empty_report(self, mock_get):
        mock_get.return_value = _mock_db({})
        m = _metrics()
        report = m.compute_portfolio_risk([])
        assert report.var_results == []
