"""Portfolio optimizer — score-weighted with volatility dampening.

Phase 2 / Sprint 3
Computes optimal target weights by combining composite scores with a
volatility-dampening factor derived from historical price variance.
No external optimisation library required — uses a closed-form
score / volatility weighting that approximates mean-variance intuition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()

_INVESTED_PCT  = 0.80     # target invested fraction of portfolio
_CASH_BUFFER   = 0.20     # minimum cash reserve
_MAX_WEIGHT    = 0.25     # hard cap per symbol
_MIN_WEIGHT    = 0.02     # below this, exclude from portfolio
_MIN_SCORE     = 50.0     # only include bullish signals (score > 50)
_LOOKBACK_DAYS = 30       # days of prices used for volatility estimate


@dataclass
class OptimizedWeight:
    ticker: str
    score: float
    volatility: float          # annualised daily std dev
    raw_weight: float          # before cap/normalisation
    final_weight: float        # after cap/normalisation
    change_from_current: float = 0.0   # signed delta vs current allocation


@dataclass
class OptimizationResult:
    weights: list[OptimizedWeight] = field(default_factory=list)
    total_invested_pct: float = 0.0
    cash_pct: float = 0.0
    method: str = "score_vol_weighted"
    skipped_symbols: list[str] = field(default_factory=list)
    notes: str = ""


class PortfolioOptimizer:
    """
    Compute target portfolio weights using composite score and volatility.

    Weight formula:
        w_i ∝ score_i / (1 + vol_i * vol_penalty)

    Higher-volatility assets receive less weight for the same score.
    Final weights are capped at MAX_WEIGHT and re-normalised to INVESTED_PCT.
    """

    def __init__(
        self,
        vol_penalty: float = 2.0,
        invested_pct: float = _INVESTED_PCT,
        max_weight: float = _MAX_WEIGHT,
        min_weight: float = _MIN_WEIGHT,
        min_score: float = _MIN_SCORE,
        lookback_days: int = _LOOKBACK_DAYS,
    ) -> None:
        self._vol_penalty   = vol_penalty
        self._invested_pct  = invested_pct
        self._max_weight    = max_weight
        self._min_weight    = min_weight
        self._min_score     = min_score
        self._lookback_days = lookback_days

    def optimize(
        self,
        current_weights: Optional[dict[str, float]] = None,
    ) -> OptimizationResult:
        """
        Run the optimisation.

        Args:
            current_weights: Optional map of ticker → current allocation fraction.

        Returns:
            OptimizationResult with per-symbol weights.
        """
        scores   = self._fetch_scores()
        vol_map  = self._fetch_volatilities([s["ticker"] for s in scores])
        current  = current_weights or {}
        skipped: list[str] = []

        candidates: list[tuple[str, float, float]] = []
        for row in scores:
            ticker = row["ticker"]
            score  = row["composite_score"]
            if score < self._min_score:
                skipped.append(ticker)
                continue
            vol = vol_map.get(ticker, 0.20)   # default 20% annualised vol
            candidates.append((ticker, score, vol))

        if not candidates:
            return OptimizationResult(
                skipped_symbols=skipped,
                notes="No bullish symbols found — all cash",
            )

        # ── Raw weights ───────────────────────────────────────────────────
        raw: dict[str, float] = {}
        for ticker, score, vol in candidates:
            raw[ticker] = score / (1.0 + self._vol_penalty * vol)

        raw_sum = sum(raw.values())
        if raw_sum <= 0:
            return OptimizationResult(skipped_symbols=skipped, notes="Zero raw weight sum")

        # Normalise to invested_pct, then cap
        capped: dict[str, float] = {}
        for ticker, rw in raw.items():
            w = (rw / raw_sum) * self._invested_pct
            capped[ticker] = min(w, self._max_weight)

        # Re-normalise after capping (excess redistributed proportionally)
        capped = self._renormalise(capped)

        # Filter out negligible weights
        capped = {t: w for t, w in capped.items() if w >= self._min_weight}
        capped = self._renormalise(capped)

        # ── Build result ──────────────────────────────────────────────────
        weights_out = []
        total_invested = 0.0
        vol_map_by_ticker = {t: v for t, s, v in candidates}
        raw_map = raw

        for ticker, final_w in sorted(capped.items(), key=lambda x: -x[1]):
            weights_out.append(OptimizedWeight(
                ticker=ticker,
                score=next(s for t, s, _ in candidates if t == ticker),
                volatility=round(vol_map_by_ticker.get(ticker, 0.20), 4),
                raw_weight=round(raw_map.get(ticker, 0.0) / raw_sum * self._invested_pct, 4),
                final_weight=round(final_w, 4),
                change_from_current=round(final_w - current.get(ticker, 0.0), 4),
            ))
            total_invested += final_w

        result = OptimizationResult(
            weights=weights_out,
            total_invested_pct=round(total_invested, 4),
            cash_pct=round(1.0 - total_invested, 4),
            skipped_symbols=skipped,
            notes=f"Optimised {len(weights_out)} symbols, skipped {len(skipped)}",
        )
        log.info("optimizer.done", symbols=len(weights_out), invested_pct=total_invested)
        return result

    # ── Private helpers ──────────────────────────────────────────────────────

    def _fetch_scores(self) -> list[dict]:
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT DISTINCT ON (s.id)
                        s.ticker,
                        a.composite_score
                    FROM analysis_scores a
                    JOIN symbols s ON s.id = a.symbol_id
                    ORDER BY s.id, a.scored_at DESC
                """)
            ).fetchall()
        finally:
            session.close()
        return [{"ticker": r[0], "composite_score": float(r[1])} for r in rows]

    def _fetch_volatilities(self, tickers: list[str]) -> dict[str, float]:
        """Compute annualised daily return volatility for each ticker."""
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
                      AND m.trade_date >= NOW() - INTERVAL '{self._lookback_days} days'
                    ORDER BY s.ticker, m.trade_date ASC
                """)
            ).fetchall()
        finally:
            session.close()

        # Group by ticker
        by_ticker: dict[str, list[float]] = {}
        for row in rows:
            ticker = row[0]
            price  = float(row[1])
            by_ticker.setdefault(ticker, []).append(price)

        vol_map: dict[str, float] = {}
        for ticker, prices in by_ticker.items():
            if len(prices) < 2:
                vol_map[ticker] = 0.20
                continue
            returns = [
                (prices[i] - prices[i - 1]) / prices[i - 1]
                for i in range(1, len(prices))
                if prices[i - 1] > 0
            ]
            if not returns:
                vol_map[ticker] = 0.20
                continue
            mean_r  = sum(returns) / len(returns)
            variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            daily_std = math.sqrt(variance)
            vol_map[ticker] = round(daily_std * math.sqrt(252), 4)  # annualise

        return vol_map

    @staticmethod
    def _renormalise(weights: dict[str, float]) -> dict[str, float]:
        total = sum(weights.values())
        if total <= 0:
            return weights
        return {t: w / total * _INVESTED_PCT for t, w in weights.items()}
