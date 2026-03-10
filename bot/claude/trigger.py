"""Smart trigger — decides when to call Claude vs. skip or use fallback.

Task S3-T1-003
Calls Claude only when:
  1. Score delta exceeds threshold (meaningful change)
  2. Daily budget has not been exhausted
  3. The composite score is in an actionable range (not solidly neutral)
"""

from __future__ import annotations

from typing import Optional
import structlog

from claude.usage_tracker import can_call_claude

log = structlog.get_logger()

# Minimum composite score change to warrant a Claude call
_DELTA_THRESHOLD = 5.0      # points (0-100 scale)

# Scores in this band are "solidly neutral" — skip Claude, hold anyway
_NEUTRAL_BAND_LOW  = 42.0
_NEUTRAL_BAND_HIGH = 58.0

# Estimated tokens per call (used for budget pre-check)
_ESTIMATED_TOKENS_PER_CALL = 2500


def should_call_claude(
    ticker: str,
    composite_score: float,
    previous_composite: Optional[float],
    force: bool = False,
) -> tuple[bool, str]:
    """
    Decide whether to invoke Claude for a recommendation.

    Returns (should_call: bool, reason: str).
    """
    if force:
        return True, "forced"

    # 1. Budget check
    if not can_call_claude(estimated_tokens=_ESTIMATED_TOKENS_PER_CALL):
        return False, "budget_exhausted"

    # 2. Delta check — only call if score moved significantly
    if previous_composite is not None:
        delta = abs(composite_score - previous_composite)
        if delta < _DELTA_THRESHOLD:
            log.info(
                "trigger.skip_small_delta",
                ticker=ticker,
                delta=round(delta, 2),
                threshold=_DELTA_THRESHOLD,
            )
            return False, f"delta_too_small ({delta:.1f} < {_DELTA_THRESHOLD})"

    # 3. Neutrality check — don't waste quota on solid holds
    if _NEUTRAL_BAND_LOW <= composite_score <= _NEUTRAL_BAND_HIGH:
        log.info(
            "trigger.skip_neutral",
            ticker=ticker,
            composite=composite_score,
        )
        return False, "solidly_neutral"

    log.info("trigger.call_approved", ticker=ticker, composite=composite_score)
    return True, "score_actionable"


def get_previous_composite(ticker: str) -> Optional[float]:
    """Fetch the most recent prior composite score for delta comparison."""
    from db import get_session
    from sqlalchemy import text

    session = get_session()
    try:
        row = session.execute(
            text("""
                SELECT a.composite_score
                FROM   analysis_scores a
                JOIN   symbols s ON s.id = a.symbol_id
                WHERE  s.ticker = :ticker
                ORDER  BY a.scored_at DESC
                OFFSET 1     -- skip the current (most recent) score
                LIMIT  1
            """),
            {"ticker": ticker},
        ).fetchone()
        return float(row[0]) if row else None
    finally:
        session.close()
