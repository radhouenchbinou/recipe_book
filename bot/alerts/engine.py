"""Alert engine — evaluates price and composite-score triggers.

Phase 3 / Sprint 1
Runs after every analysis pipeline cycle.  For each active alert it:
  1. Fetches the current market value (price or score).
  2. Evaluates the condition against the stored threshold.
  3. On breach: records triggered_at + last_value in the DB, emits a
     structured log event, and (optionally) invokes a webhook callback.

Supported conditions:
  price_above   — close_price > threshold
  price_below   — close_price < threshold
  score_above   — composite_score > threshold
  score_below   — composite_score < threshold
  change_pct    — |day_change_pct| > threshold  (absolute %)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()

Webhook = Callable[[dict], None]   # optional notification callback

_SUPPORTED_CONDITIONS = frozenset({
    "price_above", "price_below",
    "score_above", "score_below",
    "change_pct",
})


@dataclass
class AlertFiring:
    alert_id:   int
    name:       str
    ticker:     str
    condition:  str
    threshold:  float
    current_value: float
    message:    str


class AlertEngine:
    """
    Evaluates all active alerts and fires notifications for breached ones.

    Parameters
    ----------
    webhook : optional callable
        Called with a dict payload for every fired alert.
        Useful for Slack / email / webhook integrations.
    cooldown_minutes : int
        Minimum minutes between repeated firings for the same alert (default 60).
    """

    def __init__(
        self,
        webhook: Optional[Webhook] = None,
        cooldown_minutes: int = 60,
    ) -> None:
        self._webhook = webhook
        self._cooldown_minutes = cooldown_minutes

    def run(self) -> list[AlertFiring]:
        """
        Evaluate all active alerts and return a list of fired alerts.

        Returns:
            List of AlertFiring objects for breached alerts.
        """
        alerts = self._load_alerts()
        if not alerts:
            log.debug("alert_engine.no_active_alerts")
            return []

        fired: list[AlertFiring] = []
        for alert in alerts:
            firing = self._evaluate(alert)
            if firing:
                self._record_firing(alert["id"], firing.current_value)
                if self._webhook:
                    try:
                        self._webhook(self._payload(firing))
                    except Exception as exc:
                        log.error("alert_engine.webhook_failed", error=str(exc), alert_id=alert["id"])
                fired.append(firing)

        log.info("alert_engine.run_complete", evaluated=len(alerts), fired=len(fired))
        return fired

    # ── Private helpers ──────────────────────────────────────────────────────

    def _load_alerts(self) -> list[dict]:
        """Fetch active alerts (respecting cooldown)."""
        session = get_session()
        try:
            rows = session.execute(
                text(f"""
                    SELECT
                        a.id, a.name, a.condition, a.threshold,
                        s.ticker,
                        a.triggered_at
                    FROM alerts a
                    JOIN symbols s ON s.id = a.symbol_id
                    WHERE a.active = TRUE
                      AND a.symbol_id IS NOT NULL
                      AND a.condition IN ({','.join(f"'{c}'" for c in _SUPPORTED_CONDITIONS)})
                      AND (
                          a.triggered_at IS NULL
                          OR a.triggered_at < NOW() - INTERVAL '{self._cooldown_minutes} minutes'
                      )
                """)
            ).fetchall()
        finally:
            session.close()

        return [
            {"id": r[0], "name": r[1], "condition": r[2],
             "threshold": float(r[3]), "ticker": r[4]}
            for r in rows
        ]

    def _evaluate(self, alert: dict) -> Optional[AlertFiring]:
        """Fetch the relevant metric and test the condition."""
        ticker    = alert["ticker"]
        condition = alert["condition"]
        threshold = alert["threshold"]

        current = self._fetch_current_value(ticker, condition)
        if current is None:
            log.debug("alert_engine.no_data", ticker=ticker, condition=condition)
            return None

        breached = False
        if condition == "price_above":
            breached = current > threshold
        elif condition == "price_below":
            breached = current < threshold
        elif condition == "score_above":
            breached = current > threshold
        elif condition == "score_below":
            breached = current < threshold
        elif condition == "change_pct":
            breached = abs(current) > threshold

        if not breached:
            return None

        message = (
            f"Alert '{alert['name']}' fired: {ticker} {condition} "
            f"(current={current:.4f}, threshold={threshold:.4f})"
        )
        log.warning("alert_engine.fired", ticker=ticker, condition=condition,
                    current=current, threshold=threshold, alert_id=alert["id"])
        return AlertFiring(
            alert_id=alert["id"],
            name=alert["name"],
            ticker=ticker,
            condition=condition,
            threshold=threshold,
            current_value=round(current, 4),
            message=message,
        )

    def _fetch_current_value(self, ticker: str, condition: str) -> Optional[float]:
        """Query the DB for the relevant metric for a ticker."""
        session = get_session()
        try:
            if condition in ("price_above", "price_below"):
                row = session.execute(
                    text("""
                        SELECT m.close_price
                        FROM market_data m
                        JOIN symbols s ON s.id = m.symbol_id
                        WHERE s.ticker = :ticker
                        ORDER BY m.trade_date DESC LIMIT 1
                    """),
                    {"ticker": ticker},
                ).fetchone()
                return float(row[0]) if row else None

            elif condition in ("score_above", "score_below"):
                row = session.execute(
                    text("""
                        SELECT a.composite_score
                        FROM analysis_scores a
                        JOIN symbols s ON s.id = a.symbol_id
                        WHERE s.ticker = :ticker
                        ORDER BY a.scored_at DESC LIMIT 1
                    """),
                    {"ticker": ticker},
                ).fetchone()
                return float(row[0]) if row else None

            elif condition == "change_pct":
                rows = session.execute(
                    text("""
                        SELECT m.close_price
                        FROM market_data m
                        JOIN symbols s ON s.id = m.symbol_id
                        WHERE s.ticker = :ticker
                        ORDER BY m.trade_date DESC LIMIT 2
                    """),
                    {"ticker": ticker},
                ).fetchall()
                if len(rows) < 2 or float(rows[1][0]) == 0:
                    return None
                return (float(rows[0][0]) - float(rows[1][0])) / float(rows[1][0]) * 100

        finally:
            session.close()
        return None

    def _record_firing(self, alert_id: int, current_value: float) -> None:
        session = get_session()
        try:
            session.execute(
                text("""
                    UPDATE alerts
                    SET triggered_at  = NOW(),
                        last_value    = :val,
                        trigger_count = COALESCE(trigger_count, 0) + 1
                    WHERE id = :id
                """),
                {"val": current_value, "id": alert_id},
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            log.error("alert_engine.record_failed", error=str(exc), alert_id=alert_id)
        finally:
            session.close()

    @staticmethod
    def _payload(firing: AlertFiring) -> dict:
        return {
            "alert_id":     firing.alert_id,
            "name":         firing.name,
            "ticker":       firing.ticker,
            "condition":    firing.condition,
            "threshold":    firing.threshold,
            "current_value": firing.current_value,
            "message":      firing.message,
        }
