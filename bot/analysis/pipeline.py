"""Analysis pipeline — orchestrates indicators, sentiment, and geo risk,
then persists composite scores to the analysis_scores table.

Task S2-T3-002 (score aggregation) + S2-T4-001 (DB persistence)
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional
import structlog
from sqlalchemy import text

from config import TRACKED_SYMBOLS
from db import get_session
from analysis.indicators import compute_indicators, IndicatorSnapshot
from analysis.sentiment import compute_sentiment_score
from analysis.geo_risk import compute_geo_risk_score, GeoRiskResult

log = structlog.get_logger()

# Weights for the composite score (must sum to 1.0)
_W_TECHNICAL = 0.40
_W_SENTIMENT = 0.35
_W_GEO_RISK  = 0.25   # geo risk is inverted: high risk → lower composite


def _sentiment_to_score(s: Optional[float]) -> float:
    """Map [-1, +1] sentiment to [0, 100] score."""
    if s is None:
        return 50.0
    return round((s + 1.0) / 2.0 * 100.0, 2)


def _geo_to_score(geo_score: float) -> float:
    """Invert geo risk: high risk lowers the composite score."""
    return round(100.0 - geo_score, 2)


def compute_composite_score(
    technical: float,
    sentiment: Optional[float],
    geo_risk: float,
) -> float:
    sent_score = _sentiment_to_score(sentiment)
    geo_score  = _geo_to_score(geo_risk)
    composite  = (
        _W_TECHNICAL * technical
        + _W_SENTIMENT * sent_score
        + _W_GEO_RISK  * geo_score
    )
    return round(min(100.0, max(0.0, composite)), 2)


def _persist_scores(
    ticker: str,
    indicators: IndicatorSnapshot,
    sentiment: Optional[float],
    geo: GeoRiskResult,
    composite: float,
) -> None:
    session = get_session()
    try:
        indicator_json = json.dumps(asdict(indicators))
        session.execute(
            text("""
                INSERT INTO analysis_scores
                    (symbol_id, technical_score, sentiment_score,
                     geo_risk_score, composite_score, indicator_snapshot)
                SELECT s.id, :technical, :sentiment, :geo_risk, :composite, :snapshot::jsonb
                FROM   symbols s
                WHERE  s.ticker = :ticker
            """),
            {
                "ticker":     ticker,
                "technical":  indicators.technical_score,
                "sentiment":  sentiment,
                "geo_risk":   geo.adjusted_score,
                "composite":  composite,
                "snapshot":   indicator_json,
            },
        )
        session.commit()
        log.info("pipeline.scores_saved", ticker=ticker, composite=composite)
    except Exception as exc:
        session.rollback()
        log.error("pipeline.db_error", ticker=ticker, error=str(exc))
        raise
    finally:
        session.close()


def analyze_symbol(ticker: str) -> Optional[float]:
    """
    Run full analysis for a single ticker.
    Returns composite score (0–100) or None on failure.
    """
    log.info("pipeline.symbol_start", ticker=ticker)

    # 1. Technical indicators
    indicators = compute_indicators(ticker)
    if indicators is None:
        log.warning("pipeline.no_indicators", ticker=ticker)
        return None

    # 2. Sentiment
    sentiment = compute_sentiment_score(ticker)

    # 3. Geopolitical risk
    geo = compute_geo_risk_score(ticker)

    # 4. Composite
    composite = compute_composite_score(
        indicators.technical_score,
        sentiment,
        geo.adjusted_score,
    )

    # 5. Persist
    _persist_scores(ticker, indicators, sentiment, geo, composite)

    log.info(
        "pipeline.symbol_done",
        ticker=ticker,
        technical=indicators.technical_score,
        sentiment=sentiment,
        geo_risk=geo.adjusted_score,
        composite=composite,
    )
    return composite


def run_analysis_pipeline() -> dict[str, Optional[float]]:
    """Run full analysis for all tracked symbols. Returns {ticker: score}."""
    results: dict[str, Optional[float]] = {}
    for ticker in TRACKED_SYMBOLS:
        try:
            results[ticker] = analyze_symbol(ticker)
        except Exception as exc:
            log.error("pipeline.symbol_failed", ticker=ticker, error=str(exc))
            results[ticker] = None
    return results
