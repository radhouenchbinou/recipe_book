"""Claude API usage tracker — enforces daily call budget.

Task S3-T3-001
Tracks tokens consumed today and blocks calls that would exceed the budget.
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple
import structlog
from sqlalchemy import text

from config import CLAUDE_DAILY_CALL_BUDGET
from db import get_session

log = structlog.get_logger()

# Approximate daily token capacity (input + output) for claude-sonnet-4-6
# at tier-1 limits. Adjust to match your actual account limits.
_DAILY_TOKEN_CAPACITY = 1_000_000


class UsageSummary(NamedTuple):
    usage_date: date
    total_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    budget_fraction: float   # 0-1 fraction of CLAUDE_DAILY_CALL_BUDGET used
    budget_remaining: float  # fraction still available


def get_today_usage() -> UsageSummary:
    """Return aggregated Claude usage for today."""
    today = date.today()
    session = get_session()
    try:
        row = session.execute(
            text("""
                SELECT COUNT(*)           AS calls,
                       COALESCE(SUM(input_tokens),  0) AS input_tokens,
                       COALESCE(SUM(output_tokens), 0) AS output_tokens
                FROM   claude_usage
                WHERE  usage_date = :today
            """),
            {"today": today},
        ).fetchone()
    finally:
        session.close()

    calls, inp, out = row
    total = inp + out
    budget_used = total / _DAILY_TOKEN_CAPACITY
    budget_remaining = max(0.0, CLAUDE_DAILY_CALL_BUDGET - budget_used)

    return UsageSummary(
        usage_date=today,
        total_calls=calls,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=total,
        budget_fraction=round(budget_used, 4),
        budget_remaining=round(budget_remaining, 4),
    )


def can_call_claude(estimated_tokens: int = 3000) -> bool:
    """
    Return True if a call of ~estimated_tokens would stay within the daily budget.
    """
    summary = get_today_usage()
    projected = (summary.total_tokens + estimated_tokens) / _DAILY_TOKEN_CAPACITY
    allowed = projected <= CLAUDE_DAILY_CALL_BUDGET
    if not allowed:
        log.warning(
            "usage_tracker.budget_exceeded",
            used_fraction=summary.budget_fraction,
            budget=CLAUDE_DAILY_CALL_BUDGET,
        )
    return allowed


def record_usage(
    input_tokens: int,
    output_tokens: int,
    symbol: str | None = None,
    trigger_reason: str | None = None,
) -> None:
    """Persist a Claude API call record."""
    session = get_session()
    try:
        session.execute(
            text("""
                INSERT INTO claude_usage
                    (input_tokens, output_tokens, symbol_id, trigger_reason)
                SELECT :inp, :out,
                       (SELECT id FROM symbols WHERE ticker = :ticker),
                       :reason
            """),
            {
                "inp": input_tokens,
                "out": output_tokens,
                "ticker": symbol,
                "reason": trigger_reason,
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        log.error("usage_tracker.record_error", error=str(exc))
    finally:
        session.close()
