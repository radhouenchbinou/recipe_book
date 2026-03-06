"""Advanced portfolio risk metrics.

Phase 2 / Sprint 3
Provides Value-at-Risk (VaR), Conditional VaR (CVaR/Expected Shortfall),
per-symbol beta against a benchmark, and a return correlation matrix.
All calculations are performed on historical daily returns stored in the DB.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()

_DEFAULT_CONFIDENCE = 0.95   # 95% VaR / CVaR
_DEFAULT_BENCHMARK  = "SPY"
_DEFAULT_LOOKBACK   = 252    # 1 year of trading days


@dataclass
class VaRResult:
    ticker: str
    confidence: float
    var_pct: float          # 1-day VaR as % of position (negative = loss)
    cvar_pct: float         # Expected shortfall beyond VaR
    lookback_days: int
    observations: int


@dataclass
class BetaResult:
    ticker: str
    benchmark: str
    beta: float
    correlation: float
    r_squared: float
    lookback_days: int


@dataclass
class CorrelationMatrix:
    tickers: list[str]
    matrix: dict[str, dict[str, float]]    # ticker → ticker → correlation


@dataclass
class PortfolioRiskReport:
    var_results:    list[VaRResult]         = field(default_factory=list)
    beta_results:   list[BetaResult]        = field(default_factory=list)
    correlation:    Optional[CorrelationMatrix] = None
    portfolio_var:  Optional[float]         = None   # weighted portfolio VaR
    portfolio_cvar: Optional[float]         = None
    notes:          str                     = ""


class RiskMetrics:
    """
    Compute advanced risk metrics from historical price data in the DB.

    Parameters
    ----------
    confidence : float
        Confidence level for VaR / CVaR (default 0.95).
    benchmark : str
        Ticker used as market benchmark for beta calculation.
    lookback_days : int
        Number of trading days of history to use.
    """

    def __init__(
        self,
        confidence: float = _DEFAULT_CONFIDENCE,
        benchmark: str = _DEFAULT_BENCHMARK,
        lookback_days: int = _DEFAULT_LOOKBACK,
    ) -> None:
        self._confidence   = confidence
        self._benchmark    = benchmark
        self._lookback     = lookback_days

    def compute_portfolio_risk(
        self,
        tickers: list[str],
        weights: Optional[dict[str, float]] = None,
    ) -> PortfolioRiskReport:
        """
        Compute full risk report for a set of tickers.

        Args:
            tickers: List of symbols to analyse.
            weights: Optional allocation fractions for weighted portfolio VaR.

        Returns:
            PortfolioRiskReport.
        """
        returns_map = self._fetch_returns(tickers + [self._benchmark])
        benchmark_ret = returns_map.get(self._benchmark, [])

        var_results:  list[VaRResult]  = []
        beta_results: list[BetaResult] = []

        for ticker in tickers:
            rets = returns_map.get(ticker, [])
            if not rets:
                continue
            var_results.append(self._compute_var(ticker, rets))
            if benchmark_ret and ticker != self._benchmark:
                beta_results.append(self._compute_beta(ticker, rets, benchmark_ret))

        corr = self._compute_correlation(returns_map, tickers)

        portfolio_var  = None
        portfolio_cvar = None
        if weights and var_results:
            portfolio_var  = sum(
                weights.get(r.ticker, 0.0) * abs(r.var_pct)  for r in var_results
            )
            portfolio_cvar = sum(
                weights.get(r.ticker, 0.0) * abs(r.cvar_pct) for r in var_results
            )

        report = PortfolioRiskReport(
            var_results=var_results,
            beta_results=beta_results,
            correlation=corr,
            portfolio_var=round(portfolio_var, 4)  if portfolio_var  is not None else None,
            portfolio_cvar=round(portfolio_cvar, 4) if portfolio_cvar is not None else None,
            notes=f"Computed for {len(var_results)} symbols, {self._lookback}d lookback, "
                  f"confidence={self._confidence*100:.0f}%",
        )
        log.info("risk_metrics.computed", symbols=len(var_results), confidence=self._confidence)
        return report

    # ── VaR / CVaR ───────────────────────────────────────────────────────────

    def _compute_var(self, ticker: str, returns: list[float]) -> VaRResult:
        sorted_rets = sorted(returns)
        n           = len(sorted_rets)
        cutoff_idx  = max(0, int(n * (1 - self._confidence)) - 1)
        var_pct     = sorted_rets[cutoff_idx]          # negative value
        tail        = sorted_rets[: cutoff_idx + 1]
        cvar_pct    = sum(tail) / len(tail) if tail else var_pct

        return VaRResult(
            ticker=ticker,
            confidence=self._confidence,
            var_pct=round(var_pct * 100, 4),
            cvar_pct=round(cvar_pct * 100, 4),
            lookback_days=self._lookback,
            observations=n,
        )

    # ── Beta / Correlation ────────────────────────────────────────────────────

    @staticmethod
    def _compute_beta(
        ticker: str,
        asset_rets: list[float],
        bench_rets: list[float],
    ) -> BetaResult:
        # Align lengths
        n = min(len(asset_rets), len(bench_rets))
        if n < 2:
            return BetaResult(ticker=ticker, benchmark=_DEFAULT_BENCHMARK,
                              beta=1.0, correlation=0.0, r_squared=0.0,
                              lookback_days=n)
        a = asset_rets[-n:]
        b = bench_rets[-n:]

        mean_a = sum(a) / n
        mean_b = sum(b) / n

        cov    = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
        var_b  = sum((b[i] - mean_b) ** 2 for i in range(n)) / n
        var_a  = sum((a[i] - mean_a) ** 2 for i in range(n)) / n

        beta       = cov / var_b if var_b > 0 else 1.0
        std_a      = math.sqrt(var_a)  if var_a  > 0 else 0
        std_b      = math.sqrt(var_b)  if var_b  > 0 else 0
        correlation = cov / (std_a * std_b) if std_a > 0 and std_b > 0 else 0.0
        r_squared   = correlation ** 2

        return BetaResult(
            ticker=ticker,
            benchmark=_DEFAULT_BENCHMARK,
            beta=round(beta, 4),
            correlation=round(correlation, 4),
            r_squared=round(r_squared, 4),
            lookback_days=n,
        )

    @staticmethod
    def _compute_correlation(
        returns_map: dict[str, list[float]],
        tickers: list[str],
    ) -> CorrelationMatrix:
        valid = [t for t in tickers if returns_map.get(t)]
        matrix: dict[str, dict[str, float]] = {}

        for t1 in valid:
            matrix[t1] = {}
            for t2 in valid:
                if t1 == t2:
                    matrix[t1][t2] = 1.0
                    continue
                r1 = returns_map[t1]
                r2 = returns_map[t2]
                n  = min(len(r1), len(r2))
                if n < 2:
                    matrix[t1][t2] = 0.0
                    continue
                a, b = r1[-n:], r2[-n:]
                ma, mb = sum(a) / n, sum(b) / n
                cov  = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / n
                va   = sum((a[i] - ma) ** 2 for i in range(n)) / n
                vb   = sum((b[i] - mb) ** 2 for i in range(n)) / n
                denom = math.sqrt(va * vb)
                matrix[t1][t2] = round(cov / denom if denom > 0 else 0.0, 4)

        return CorrelationMatrix(tickers=valid, matrix=matrix)

    # ── DB fetch ──────────────────────────────────────────────────────────────

    def _fetch_returns(self, tickers: list[str]) -> dict[str, list[float]]:
        if not tickers:
            return {}
        session = get_session()
        try:
            placeholders = ",".join(f"'{t}'" for t in tickers)
            rows = session.execute(
                text(f"""
                    SELECT s.ticker, m.close_price, m.trade_date
                    FROM market_data m
                    JOIN symbols s ON s.id = m.symbol_id
                    WHERE s.ticker IN ({placeholders})
                      AND m.trade_date >= NOW() - INTERVAL '{self._lookback + 5} days'
                    ORDER BY s.ticker, m.trade_date ASC
                """)
            ).fetchall()
        finally:
            session.close()

        # Group prices by ticker
        by_ticker: dict[str, list[float]] = {}
        for row in rows:
            by_ticker.setdefault(row[0], []).append(float(row[1]))

        # Convert to daily returns
        returns_map: dict[str, list[float]] = {}
        for ticker, prices in by_ticker.items():
            if len(prices) < 2:
                continue
            returns_map[ticker] = [
                (prices[i] - prices[i - 1]) / prices[i - 1]
                for i in range(1, len(prices))
                if prices[i - 1] > 0
            ]
        return returns_map
