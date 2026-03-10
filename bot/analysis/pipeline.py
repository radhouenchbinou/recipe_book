"""Analysis pipeline — orchestrates indicators, sentiment, geo risk, and fundamentals,
then persists composite scores to the analysis_scores table and publishes RabbitMQ events.
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
from analysis.fundamentals import FundamentalAnalyzer

log = structlog.get_logger()

# Composite score weights (must sum to 1.0)
_W_TECHNICAL    = 0.35
_W_SENTIMENT    = 0.30
_W_GEO_RISK     = 0.20
_W_FUNDAMENTAL  = 0.15

_fundamental_analyzer = FundamentalAnalyzer()


def _sentiment_to_score(s: Optional[float]) -> float:
    if s is None:
        return 50.0
    return round((s + 1.0) / 2.0 * 100.0, 2)


def _geo_to_score(geo_score: float) -> float:
    return round(100.0 - geo_score, 2)


def compute_composite_score(
    technical: float,
    sentiment: Optional[float],
    geo_risk: float,
    fundamental: Optional[float] = None,
) -> float:
    sent_score  = _sentiment_to_score(sentiment)
    geo_score   = _geo_to_score(geo_risk)
    fund_score  = fundamental if fundamental is not None else 50.0

    composite = (
        _W_TECHNICAL   * technical
        + _W_SENTIMENT * sent_score
        + _W_GEO_RISK  * geo_score
        + _W_FUNDAMENTAL * fund_score
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
                "ticker":    ticker,
                "technical": indicators.technical_score,
                "sentiment": sentiment,
                "geo_risk":  geo.adjusted_score,
                "composite": composite,
                "snapshot":  indicator_json,
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


def _publish_analysis_done(ticker: str, composite: float) -> None:
    """Non-fatal RabbitMQ publish after DB write."""
    try:
        from messaging.publisher import get_publisher
        get_publisher().publish("analysis.done", {"symbol": ticker, "composite": composite})
    except Exception as exc:
        log.warning("pipeline.publish_failed", ticker=ticker, error=str(exc))


def analyze_symbol(ticker: str) -> Optional[float]:
    """
    Run full analysis for a single ticker.
    Returns composite score (0–100) or None on failure.
    """
    log.info("pipeline.symbol_start", ticker=ticker)

    indicators = compute_indicators(ticker)
    if indicators is None:
        log.warning("pipeline.no_indicators", ticker=ticker)
        return None

    sentiment  = compute_sentiment_score(ticker)
    geo        = compute_geo_risk_score(ticker)
    fund       = _fundamental_analyzer.analyze(ticker)

    composite = compute_composite_score(
        indicators.technical_score,
        sentiment,
        geo.adjusted_score,
        fund.score if fund else None,
    )

    _persist_scores(ticker, indicators, sentiment, geo, composite)
    _publish_analysis_done(ticker, composite)

    log.info(
        "pipeline.symbol_done",
        ticker=ticker,
        technical=indicators.technical_score,
        sentiment=sentiment,
        geo_risk=geo.adjusted_score,
        fundamental=fund.score if fund else None,
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
