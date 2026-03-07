"""Parses Claude's JSON recommendation response and persists to DB.

Task S3-T2-001 + S3-T2-002
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()

VALID_ACTIONS = {"buy", "sell", "hold"}


@dataclass
class Recommendation:
    action: str          # buy | sell | hold
    confidence: float    # 0.0 – 1.0
    reasoning: str
    key_risks: list[str]
    suggested_position_size: float
    source: str = "claude"


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a string (handles markdown fences)."""
    # Strip markdown code fences if present
    clean = re.sub(r"```(?:json)?\s*", "", text).strip()
    # Find first { ... }
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Claude response")
    return json.loads(match.group())


def parse_response(raw: str) -> Recommendation:
    """
    Parse Claude's raw response into a Recommendation.
    Raises ValueError if the response is malformed.
    """
    data = _extract_json(raw)

    action = str(data.get("action", "hold")).lower().strip()
    if action not in VALID_ACTIONS:
        log.warning("parser.invalid_action", action=action)
        action = "hold"

    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    reasoning = str(data.get("reasoning", "No reasoning provided."))[:1000]

    key_risks = [str(r) for r in data.get("key_risks", [])][:5]

    position_size = float(data.get("suggested_position_size", 0.05))
    position_size = max(0.0, min(0.10, position_size))

    return Recommendation(
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        key_risks=key_risks,
        suggested_position_size=position_size,
        source="claude",
    )


def persist_recommendation(
    ticker: str,
    rec: Recommendation,
    score_id: Optional[str] = None,
    raw_response: Optional[str] = None,
) -> str:
    """Save a recommendation to DB. Returns the new record UUID."""
    session = get_session()
    try:
        raw_json = json.dumps({
            "raw": raw_response,
            "key_risks": rec.key_risks,
            "suggested_position_size": rec.suggested_position_size,
        })
        row = session.execute(
            text("""
                INSERT INTO recommendations
                    (symbol_id, score_id, action, confidence,
                     reasoning, source, raw_response)
                SELECT s.id,
                       :score_id::uuid,
                       :action,
                       :confidence,
                       :reasoning,
                       :source,
                       :raw_json::jsonb
                FROM   symbols s
                WHERE  s.ticker = :ticker
                RETURNING id
            """),
            {
                "ticker":     ticker,
                "score_id":   score_id,
                "action":     rec.action,
                "confidence": rec.confidence,
                "reasoning":  rec.reasoning,
                "source":     rec.source,
                "raw_json":   raw_json,
            },
        ).fetchone()
        session.commit()
        rec_id = str(row[0])
        log.info(
            "parser.recommendation_saved",
            ticker=ticker,
            action=rec.action,
            confidence=rec.confidence,
            id=rec_id,
        )
        # Publish to RabbitMQ so API can push to Socket.io (non-fatal)
        try:
            from messaging.publisher import get_publisher
            get_publisher().publish("rec.new", {
                "symbol": ticker,
                "action": rec.action,
                "confidence": rec.confidence,
                "id": rec_id,
            })
        except Exception as pub_exc:
            log.warning("parser.publish_failed", ticker=ticker, error=str(pub_exc))

        return rec_id
    except Exception as exc:
        session.rollback()
        log.error("parser.db_error", ticker=ticker, error=str(exc))
        raise
    finally:
        session.close()
