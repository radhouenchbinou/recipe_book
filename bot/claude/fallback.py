"""Fallback rule-based recommender — used when Claude quota is exhausted.

Task S3-T2-003
Produces deterministic buy/sell/hold decisions from composite + technical scores
without any LLM call.
"""

from __future__ import annotations

import structlog
from claude.parser import Recommendation

log = structlog.get_logger()

# Thresholds (composite score 0-100)
_BUY_THRESHOLD  = 65.0   # strong bullish signal
_SELL_THRESHOLD = 35.0   # strong bearish signal
# Between 35-65 → hold

# Minimum confidence we assign for rule-based decisions
_BASE_CONFIDENCE = 0.55


def _confidence_from_score(composite: float) -> float:
    """Derive confidence from how far the score is from neutral (50)."""
    distance = abs(composite - 50.0)
    # 15 pts away → 0.55, 50 pts away (max) → 0.95
    conf = _BASE_CONFIDENCE + (distance / 50.0) * (0.95 - _BASE_CONFIDENCE)
    return round(min(0.95, conf), 3)


def generate_fallback_recommendation(
    ticker: str,
    composite_score: float,
    technical_score: float,
    geo_risk_score: float,
    sentiment_score: float | None,
) -> Recommendation:
    """
    Generate a rule-based recommendation without calling Claude.
    Always returns a valid Recommendation with source='fallback'.
    """
    confidence = _confidence_from_score(composite_score)

    if composite_score >= _BUY_THRESHOLD:
        action = "buy"
        reasoning = (
            f"Composite score {composite_score:.1f}/100 indicates strong bullish momentum. "
            f"Technical score: {technical_score:.1f}. "
            f"Geo risk: {geo_risk_score:.1f}/100 (rule-based fallback — Claude quota exhausted)."
        )
        position_size = min(0.08, 0.05 + (composite_score - 65) * 0.001)

    elif composite_score <= _SELL_THRESHOLD:
        action = "sell"
        reasoning = (
            f"Composite score {composite_score:.1f}/100 indicates bearish conditions. "
            f"Technical score: {technical_score:.1f}. "
            f"Geo risk: {geo_risk_score:.1f}/100 (rule-based fallback — Claude quota exhausted)."
        )
        position_size = 0.0   # exit position

    else:
        action = "hold"
        reasoning = (
            f"Composite score {composite_score:.1f}/100 is within neutral range (35-65). "
            f"Insufficient signal to act (rule-based fallback — Claude quota exhausted)."
        )
        position_size = 0.0

    risks = []
    if geo_risk_score > 50:
        risks.append(f"Elevated geopolitical risk ({geo_risk_score:.0f}/100)")
    if sentiment_score is not None and sentiment_score < -0.3:
        risks.append("Negative news sentiment")
    if geo_risk_score <= 50 and (sentiment_score is None or sentiment_score >= -0.3):
        risks.append("Rule-based model — limited context vs. Claude")

    rec = Recommendation(
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        key_risks=risks,
        suggested_position_size=round(position_size, 3),
        source="fallback",
    )
    log.info(
        "fallback.recommendation",
        ticker=ticker,
        action=action,
        confidence=confidence,
        composite=composite_score,
    )
    return rec
