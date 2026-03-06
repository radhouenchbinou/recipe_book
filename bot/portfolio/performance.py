"""Portfolio performance analytics aggregator.

Phase 2 / Sprint 1
Aggregates backtest results and live trading metrics into a unified
performance report: Sharpe ratio, max drawdown, win rate, and P&L summary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()


@dataclass
class SymbolPerformance:
    ticker: str
    recommendation_count: int
    buy_count: int
    sell_count: int
    hold_count: int
    claude_count: int
    fallback_count: int
    avg_confidence: float
    avg_composite_score: float


@dataclass
class PerformanceSummary:
    """Aggregated performance metrics for the portfolio."""
    # P&L metrics (from broker account snapshot)
    portfolio_value: float
    cash: float
    equity: float
    day_pl: float
    day_pl_pct: float
    total_pl: float
    total_pl_pct: float

    # Recommendation quality
    total_recommendations: int
    buy_recommendations: int
    sell_recommendations: int
    hold_recommendations: int
    claude_recommendations: int
    fallback_recommendations: int

    # Per-symbol breakdown
    symbols: list[SymbolPerformance] = field(default_factory=list)

    # Backtest summary (populated when backtest data available)
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    win_rate_pct: Optional[float] = None
    annualised_return_pct: Optional[float] = None


class PerformanceAnalytics:
    """Compute and aggregate portfolio performance metrics."""

    def __init__(self, initial_capital: float = 100_000.0) -> None:
        self._initial_capital = initial_capital

    def compute_summary(
        self,
        portfolio_value: float,
        cash: float,
        equity: float,
        day_pl: float,
        day_pl_pct: float,
    ) -> PerformanceSummary:
        """Build a full performance summary combining live + DB analytics."""
        total_pl = portfolio_value - self._initial_capital
        total_pl_pct = (total_pl / self._initial_capital) * 100 if self._initial_capital else 0.0

        rec_stats = self._recommendation_stats()
        symbol_stats = self._per_symbol_stats()

        summary = PerformanceSummary(
            portfolio_value=round(portfolio_value, 2),
            cash=round(cash, 2),
            equity=round(equity, 2),
            day_pl=round(day_pl, 2),
            day_pl_pct=round(day_pl_pct, 4),
            total_pl=round(total_pl, 2),
            total_pl_pct=round(total_pl_pct, 4),
            total_recommendations=rec_stats["total"],
            buy_recommendations=rec_stats["buy"],
            sell_recommendations=rec_stats["sell"],
            hold_recommendations=rec_stats["hold"],
            claude_recommendations=rec_stats["claude"],
            fallback_recommendations=rec_stats["fallback"],
            symbols=symbol_stats,
        )

        log.info(
            "performance.summary_computed",
            portfolio_value=portfolio_value,
            total_pl=summary.total_pl,
            total_recommendations=summary.total_recommendations,
        )
        return summary

    def compute_backtest_metrics(
        self, equity_curve: list[float], trades: list[dict]
    ) -> dict:
        """
        Compute Sharpe ratio, max drawdown, and win rate from raw backtest data.

        Args:
            equity_curve: Daily portfolio values
            trades: List of trade dicts with keys: action, pnl, entry_price, exit_price

        Returns:
            dict with sharpe_ratio, max_drawdown_pct, win_rate_pct, annualised_return_pct
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                "sharpe_ratio": None,
                "max_drawdown_pct": None,
                "win_rate_pct": None,
                "annualised_return_pct": None,
            }

        sharpe = self._compute_sharpe(equity_curve)
        drawdown = self._compute_max_drawdown(equity_curve)
        win_rate = self._compute_win_rate(trades)
        ann_return = self._compute_annualised_return(equity_curve)

        return {
            "sharpe_ratio": round(sharpe, 4) if sharpe is not None else None,
            "max_drawdown_pct": round(drawdown, 4) if drawdown is not None else None,
            "win_rate_pct": round(win_rate, 4) if win_rate is not None else None,
            "annualised_return_pct": round(ann_return, 4) if ann_return is not None else None,
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _compute_sharpe(equity_curve: list[float], risk_free_rate: float = 0.05) -> Optional[float]:
        """Annualised Sharpe ratio (252 trading days)."""
        if len(equity_curve) < 2:
            return None
        returns = [
            (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1] > 0
        ]
        if not returns:
            return None
        n = len(returns)
        mean_r = sum(returns) / n
        variance = sum((r - mean_r) ** 2 for r in returns) / n
        std_r = math.sqrt(variance) if variance > 0 else 0
        if std_r == 0:
            return None
        daily_rf = risk_free_rate / 252
        return (mean_r - daily_rf) / std_r * math.sqrt(252)

    @staticmethod
    def _compute_max_drawdown(equity_curve: list[float]) -> Optional[float]:
        """Maximum peak-to-trough drawdown as a percentage."""
        if not equity_curve:
            return None
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    @staticmethod
    def _compute_win_rate(trades: list[dict]) -> Optional[float]:
        """Percentage of closed trades that were profitable."""
        closed = [t for t in trades if t.get("action") in ("sell", "close")]
        if not closed:
            return None
        wins = sum(1 for t in closed if t.get("pnl", 0) > 0)
        return wins / len(closed) * 100

    @staticmethod
    def _compute_annualised_return(equity_curve: list[float]) -> Optional[float]:
        """CAGR based on number of trading days in the equity curve."""
        if len(equity_curve) < 2 or equity_curve[0] <= 0:
            return None
        total_return = equity_curve[-1] / equity_curve[0]
        days = len(equity_curve)
        ann = (total_return ** (252 / days)) - 1
        return ann * 100

    def _recommendation_stats(self) -> dict:
        session = get_session()
        try:
            row = session.execute(
                text("""
                    SELECT
                        COUNT(*)                                       AS total,
                        SUM(CASE WHEN action='buy'  THEN 1 ELSE 0 END) AS buy,
                        SUM(CASE WHEN action='sell' THEN 1 ELSE 0 END) AS sell,
                        SUM(CASE WHEN action='hold' THEN 1 ELSE 0 END) AS hold,
                        SUM(CASE WHEN source='claude'   THEN 1 ELSE 0 END) AS claude,
                        SUM(CASE WHEN source='fallback' THEN 1 ELSE 0 END) AS fallback
                    FROM recommendations
                """)
            ).fetchone()
        finally:
            session.close()

        if not row:
            return {"total": 0, "buy": 0, "sell": 0, "hold": 0, "claude": 0, "fallback": 0}
        return {
            "total":    int(row[0] or 0),
            "buy":      int(row[1] or 0),
            "sell":     int(row[2] or 0),
            "hold":     int(row[3] or 0),
            "claude":   int(row[4] or 0),
            "fallback": int(row[5] or 0),
        }

    def _per_symbol_stats(self) -> list[SymbolPerformance]:
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT
                        s.ticker,
                        COUNT(r.id)                                            AS rec_count,
                        SUM(CASE WHEN r.action='buy'  THEN 1 ELSE 0 END)      AS buy_count,
                        SUM(CASE WHEN r.action='sell' THEN 1 ELSE 0 END)      AS sell_count,
                        SUM(CASE WHEN r.action='hold' THEN 1 ELSE 0 END)      AS hold_count,
                        SUM(CASE WHEN r.source='claude'   THEN 1 ELSE 0 END)  AS claude_count,
                        SUM(CASE WHEN r.source='fallback' THEN 1 ELSE 0 END)  AS fallback_count,
                        AVG(r.confidence)                                      AS avg_confidence,
                        AVG(a.composite_score)                                 AS avg_composite
                    FROM recommendations r
                    JOIN symbols s ON s.id = r.symbol_id
                    LEFT JOIN analysis_scores a ON a.id = r.analysis_score_id
                    GROUP BY s.ticker
                    ORDER BY rec_count DESC
                """)
            ).fetchall()
        finally:
            session.close()

        result = []
        for row in rows:
            result.append(SymbolPerformance(
                ticker=row[0],
                recommendation_count=int(row[1] or 0),
                buy_count=int(row[2] or 0),
                sell_count=int(row[3] or 0),
                hold_count=int(row[4] or 0),
                claude_count=int(row[5] or 0),
                fallback_count=int(row[6] or 0),
                avg_confidence=round(float(row[7] or 0), 4),
                avg_composite_score=round(float(row[8] or 0), 2),
            ))
        return result
