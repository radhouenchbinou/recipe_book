"""Top-level recommender — orchestrates Claude + trigger + fallback.

Wires together:
  1. Smart trigger → decide whether to call Claude
  2. Claude client → get AI recommendation
  3. Fallback → rule-based recommendation when Claude is skipped
  4. Parser + persistence → save result to DB
"""

from __future__ import annotations

from datetime import date
from typing import Optional
import structlog
from sqlalchemy import text

from claude.client import get_recommendation, ClaudeAPIError
from claude.fallback import generate_fallback_recommendation
from claude.parser import parse_response, persist_recommendation, Recommendation
from claude.prompt_builder import AnalysisContext
from claude.trigger import should_call_claude, get_previous_composite
from db import get_session

log = structlog.get_logger()


def _load_latest_scores(ticker: str) -> Optional[dict]:
    """Load the most recent analysis_scores row for ticker."""
    session = get_session()
    try:
        row = session.execute(
            text("""
                SELECT a.id::text,
                       a.technical_score,
                       a.sentiment_score,
                       a.geo_risk_score,
                       a.composite_score,
                       a.indicator_snapshot,
                       a.scored_at,
                       md.close
                FROM   analysis_scores a
                JOIN   symbols s ON s.id = a.symbol_id
                LEFT JOIN LATERAL (
                    SELECT close FROM market_data md2
                    JOIN   symbols s2 ON s2.id = md2.symbol_id
                    WHERE  s2.ticker = :ticker
                    ORDER  BY trade_date DESC LIMIT 1
                ) md ON TRUE
                WHERE  s.ticker = :ticker
                ORDER  BY a.scored_at DESC
                LIMIT  1
            """),
            {"ticker": ticker},
        ).fetchone()
        if not row:
            return None
        return {
            "score_id": row[0],
            "technical": float(row[1]) if row[1] else 50.0,
            "sentiment": float(row[2]) if row[2] else None,
            "geo_risk":  float(row[3]) if row[3] else 0.0,
            "composite": float(row[4]) if row[4] else 50.0,
            "indicator_snapshot": row[5],
            "scored_at": row[6],
            "close": float(row[7]) if row[7] else 0.0,
        }
    finally:
        session.close()


def _extract_indicator(snapshot: dict | None, key: str) -> Optional[float]:
    if not snapshot:
        return None
    v = snapshot.get(key)
    return float(v) if v is not None else None


def recommend_for_ticker(ticker: str, force_claude: bool = False) -> Optional[Recommendation]:
    """
    Generate a recommendation for *ticker*.
    Uses Claude if trigger approves, otherwise falls back to rule-based logic.
    Returns None if no score data is available.
    """
    scores = _load_latest_scores(ticker)
    if not scores:
        log.warning("recommender.no_scores", ticker=ticker)
        return None

    prev_composite = get_previous_composite(ticker)
    should_call, reason = should_call_claude(
        ticker=ticker,
        composite_score=scores["composite"],
        previous_composite=prev_composite,
        force=force_claude,
    )

    snapshot = scores.get("indicator_snapshot") or {}

    if should_call:
        ctx = AnalysisContext(
            ticker=ticker,
            close_price=scores["close"],
            technical_score=scores["technical"],
            sentiment_score=scores["sentiment"],
            geo_risk_score=scores["geo_risk"],
            composite_score=scores["composite"],
            rsi=_extract_indicator(snapshot, "rsi_14"),
            macd=_extract_indicator(snapshot, "macd"),
            macd_hist=_extract_indicator(snapshot, "macd_hist"),
            bb_pct_b=_extract_indicator(snapshot, "bb_pct_b"),
            triggered_geo_events=[],
            previous_composite=prev_composite,
            as_of_date=date.today(),
        )
        try:
            raw = get_recommendation(ctx)
            rec = parse_response(raw)
            persist_recommendation(
                ticker=ticker,
                rec=rec,
                score_id=scores["score_id"],
                raw_response=raw,
            )
            log.info("recommender.claude_done", ticker=ticker, action=rec.action)
            return rec
        except (ClaudeAPIError, ValueError) as exc:
            log.warning("recommender.claude_failed_fallback", ticker=ticker, error=str(exc))
            # Fall through to fallback below

    # Fallback path
    rec = generate_fallback_recommendation(
        ticker=ticker,
        composite_score=scores["composite"],
        technical_score=scores["technical"],
        geo_risk_score=scores["geo_risk"],
        sentiment_score=scores["sentiment"],
    )
    persist_recommendation(ticker=ticker, rec=rec, score_id=scores["score_id"])
    log.info("recommender.fallback_done", ticker=ticker, action=rec.action, reason=reason)
    return rec


def run_recommendation_pipeline(force_claude: bool = False) -> dict[str, Optional[str]]:
    """Run recommendations for all tracked symbols. Returns {ticker: action}."""
    from config import TRACKED_SYMBOLS
    results = {}
    for ticker in TRACKED_SYMBOLS:
        try:
            rec = recommend_for_ticker(ticker, force_claude=force_claude)
            results[ticker] = rec.action if rec else None
        except Exception as exc:
            log.error("recommender.pipeline_error", ticker=ticker, error=str(exc))
            results[ticker] = None
    return results
