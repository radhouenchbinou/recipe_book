"""Geopolitical risk scorer — keyword-based event detection from news.

Task S2-T3-001
Scores geopolitical risk on a 0–100 scale (0 = calm, 100 = extreme risk).
Applies symbol-specific impact weights to produce per-ticker risk scores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()


# ── Event taxonomy ─────────────────────────────────────────────────────────

@dataclass
class RiskEvent:
    name: str
    keywords: list[str]
    base_score: float   # 0–100


GEO_RISK_EVENTS: list[RiskEvent] = [
    RiskEvent("war_conflict",   ["war", "invasion", "military strike", "airstrike", "troops deployed", "nato", "missile"], 90.0),
    RiskEvent("sanctions",      ["sanctions", "trade ban", "export controls", "embargo", "tariff"], 70.0),
    RiskEvent("recession_fear", ["recession", "gdp contraction", "yield curve inversion", "stagflation"], 65.0),
    RiskEvent("rate_hike",      ["rate hike", "interest rate increase", "fed tightening", "hawkish fed"], 55.0),
    RiskEvent("political_risk", ["election uncertainty", "government shutdown", "debt ceiling", "impeachment"], 50.0),
    RiskEvent("supply_chain",   ["supply chain disruption", "chip shortage", "port blockage", "factory shutdown"], 45.0),
    RiskEvent("inflation",      ["inflation surge", "cpi rise", "cost of living", "price spike"], 40.0),
    RiskEvent("cyber_attack",   ["cyberattack", "ransomware", "data breach", "infrastructure hack"], 60.0),
    RiskEvent("pandemic",       ["pandemic", "lockdown", "virus outbreak", "health emergency"], 75.0),
    RiskEvent("energy_crisis",  ["energy crisis", "oil shortage", "gas prices surge", "opec cut"], 55.0),
]

# Per-symbol sensitivity multipliers (some assets react more to geo risk)
SYMBOL_SENSITIVITY: dict[str, float] = {
    "GLD":  1.5,   # gold spikes on uncertainty
    "SPY":  1.0,
    "QQQ":  0.9,   # tech slightly less geo-sensitive
    "AAPL": 0.8,
    "MSFT": 0.8,
    "NVDA": 1.1,   # chips / export controls highly relevant
}


# ── Detection ──────────────────────────────────────────────────────────────

def detect_events(text: str) -> list[tuple[RiskEvent, float]]:
    """
    Scan text for geo-risk events.
    Returns list of (event, confidence 0–1) tuples.
    """
    text_lower = text.lower()
    found = []
    for event in GEO_RISK_EVENTS:
        hits = sum(1 for kw in event.keywords if kw in text_lower)
        if hits > 0:
            confidence = min(1.0, hits / max(len(event.keywords) * 0.3, 1))
            found.append((event, round(confidence, 3)))
    return found


def _aggregate_events(events: list[tuple[RiskEvent, float]]) -> float:
    """Combine multiple event scores into a single 0–100 risk score."""
    if not events:
        return 0.0
    # Diminishing returns: each additional event adds less
    scores = sorted([e.base_score * c for e, c in events], reverse=True)
    total = scores[0]
    for i, s in enumerate(scores[1:], 1):
        total += s * (0.5 ** i)
    return round(min(100.0, total), 2)


# ── Main entry point ───────────────────────────────────────────────────────

@dataclass
class GeoRiskResult:
    ticker: str
    raw_score: float            # 0–100 base score before symbol weighting
    adjusted_score: float       # 0–100 after symbol sensitivity multiplier
    triggered_events: list[str] = field(default_factory=list)
    article_count: int = 0


def compute_geo_risk_score(
    ticker: str,
    hours_back: int = 48,
) -> GeoRiskResult:
    """
    Compute geopolitical risk score for *ticker* from recent news.
    Always returns a result (defaults to 0 if no news).
    """
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)

    session = get_session()
    try:
        # Fetch recent global news (not just ticker-linked — geo risk is global)
        rows = session.execute(
            text("""
                SELECT headline, summary
                FROM   news_items
                WHERE  published_at >= :since
                ORDER  BY published_at DESC
                LIMIT  100
            """),
            {"since": since},
        ).fetchall()
    finally:
        session.close()

    all_events: list[tuple[RiskEvent, float]] = []
    for headline, summary in rows:
        combined = f"{headline}. {summary or ''}"
        all_events.extend(detect_events(combined))

    # De-duplicate: keep highest confidence per event type
    best: dict[str, tuple[RiskEvent, float]] = {}
    for event, conf in all_events:
        if event.name not in best or conf > best[event.name][1]:
            best[event.name] = (event, conf)

    top_events = list(best.values())
    raw_score = _aggregate_events(top_events)

    sensitivity = SYMBOL_SENSITIVITY.get(ticker, 1.0)
    adjusted = round(min(100.0, raw_score * sensitivity), 2)

    result = GeoRiskResult(
        ticker=ticker,
        raw_score=raw_score,
        adjusted_score=adjusted,
        triggered_events=[e.name for e, _ in top_events],
        article_count=len(rows),
    )
    log.info(
        "geo_risk.computed",
        ticker=ticker,
        raw=raw_score,
        adjusted=adjusted,
        events=result.triggered_events,
    )
    return result
