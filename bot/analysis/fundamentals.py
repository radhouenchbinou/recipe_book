"""Fundamental analysis scorer using yfinance .info data.

Scores 0-100 based on: P/E ratio, EPS growth, revenue growth,
debt-to-equity, and return on equity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import structlog
import yfinance as yf

log = structlog.get_logger()


@dataclass
class FundamentalScore:
    ticker: str
    score: float           # 0-100
    pe_ratio: Optional[float]
    eps_growth: Optional[float]
    revenue_growth: Optional[float]
    debt_to_equity: Optional[float]
    return_on_equity: Optional[float]


class FundamentalAnalyzer:
    """Score an equity's fundamental health on a 0-100 scale."""

    # Scoring reference points (tunable)
    _PE_GOOD = 15.0      # P/E below this is cheap
    _PE_BAD  = 40.0      # P/E above this is expensive
    _DE_GOOD = 0.5       # D/E below 0.5 = low leverage
    _DE_BAD  = 2.0       # D/E above 2.0 = high leverage
    _ROE_GOOD = 0.20     # ROE >= 20% is excellent
    _ROE_BAD  = 0.05     # ROE <  5% is poor

    def analyze(self, ticker: str) -> Optional[FundamentalScore]:
        """
        Fetch fundamental data via yfinance and return a FundamentalScore.
        Returns None if data is unavailable (e.g. gold ETF GLD).
        """
        try:
            info = yf.Ticker(ticker).info
        except Exception as exc:
            log.warning("fundamentals.fetch_failed", ticker=ticker, error=str(exc))
            return None

        pe     = info.get("trailingPE")
        eps_g  = info.get("earningsQuarterlyGrowth")
        rev_g  = info.get("revenueGrowth")
        de     = info.get("debtToEquity")
        roe    = info.get("returnOnEquity")

        score = self._compute_score(pe, eps_g, rev_g, de, roe)
        log.info("fundamentals.scored", ticker=ticker, score=score)

        return FundamentalScore(
            ticker=ticker,
            score=score,
            pe_ratio=pe,
            eps_growth=eps_g,
            revenue_growth=rev_g,
            debt_to_equity=de,
            return_on_equity=roe,
        )

    def _compute_score(
        self,
        pe: Optional[float],
        eps_g: Optional[float],
        rev_g: Optional[float],
        de: Optional[float],
        roe: Optional[float],
    ) -> float:
        """Weighted sub-score aggregation. Returns 0-100."""
        components: list[tuple[float, float]] = []  # (sub_score, weight)

        if pe is not None and pe > 0:
            pe_score = max(0.0, min(100.0, 100.0 - (pe - self._PE_GOOD) * 100.0 / (self._PE_BAD - self._PE_GOOD)))
            components.append((pe_score, 0.25))

        if eps_g is not None:
            eps_score = min(100.0, max(0.0, 50.0 + eps_g * 100.0))
            components.append((eps_score, 0.25))

        if rev_g is not None:
            rev_score = min(100.0, max(0.0, 50.0 + rev_g * 100.0))
            components.append((rev_score, 0.20))

        if de is not None and de >= 0:
            # yfinance returns D/E as a percentage (e.g. 150 = 1.5x)
            de_norm = de / 100.0 if de > 10 else de
            de_score = max(0.0, min(100.0, 100.0 - (de_norm - self._DE_GOOD) * 50.0 / (self._DE_BAD - self._DE_GOOD)))
            components.append((de_score, 0.15))

        if roe is not None:
            roe_score = min(100.0, max(0.0, (roe - self._ROE_BAD) * 100.0 / (self._ROE_GOOD - self._ROE_BAD)))
            components.append((roe_score, 0.15))

        if not components:
            return 50.0  # Neutral default when no data available

        total_weight = sum(w for _, w in components)
        weighted_sum = sum(s * w for s, w in components)
        return round(weighted_sum / total_weight, 2)
