"""Builds structured prompts for Claude from analysis scores.

Task S3-T1-002
Keeps prompts under 2000 input tokens to control cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class AnalysisContext:
    ticker: str
    close_price: float
    technical_score: float       # 0-100
    sentiment_score: Optional[float]  # -1 to +1
    geo_risk_score: float        # 0-100
    composite_score: float       # 0-100
    rsi: Optional[float]
    macd: Optional[float]
    macd_hist: Optional[float]
    bb_pct_b: Optional[float]
    triggered_geo_events: list[str]
    previous_composite: Optional[float]  # prior period score for delta context
    as_of_date: date


_SYSTEM_PROMPT = """You are a quantitative trading analyst AI. Your role is to provide
concise, data-driven buy/sell/hold recommendations for US equities and ETFs.

Rules:
- Base decisions ONLY on the data provided
- Account for geopolitical risk as a downside factor
- Consider technical momentum and market sentiment together
- Be conservative: only recommend 'buy' or 'sell' when confidence >= 0.65
- Default to 'hold' when signals are mixed or insufficient
- Never recommend more than 10% position size
- Paper trading context: recommendations are for simulation only"""


def build_prompt(ctx: AnalysisContext) -> str:
    """Build a structured recommendation prompt. Stays under ~1800 tokens."""
    delta_str = ""
    if ctx.previous_composite is not None:
        delta = ctx.composite_score - ctx.previous_composite
        direction = "up" if delta > 0 else "down"
        delta_str = f"\n- Composite score trend: {direction} {abs(delta):.1f} pts from prior period"

    geo_events_str = (
        ", ".join(ctx.triggered_geo_events) if ctx.triggered_geo_events else "none detected"
    )

    sentiment_str = (
        f"{ctx.sentiment_score:+.3f}" if ctx.sentiment_score is not None else "unavailable"
    )

    return f"""Analyze the following market data for {ctx.ticker} as of {ctx.as_of_date} and provide a trading recommendation.

## Market Data
- Ticker: {ctx.ticker}
- Current price: ${ctx.close_price:.2f}
- As of: {ctx.as_of_date}

## Composite Analysis Scores (0-100 scale, higher = more bullish)
- Technical score: {ctx.technical_score:.1f}/100
- Sentiment score: {sentiment_str} (scale: -1.0 bearish to +1.0 bullish)
- Geopolitical risk score: {ctx.geo_risk_score:.1f}/100 (higher = more risk)
- Composite score: {ctx.composite_score:.1f}/100{delta_str}

## Technical Indicators
- RSI (14): {ctx.rsi:.1f if ctx.rsi else 'N/A'}
- MACD: {ctx.macd:.4f if ctx.macd else 'N/A'}
- MACD histogram: {ctx.macd_hist:.4f if ctx.macd_hist else 'N/A'}
- Bollinger %B: {ctx.bb_pct_b:.3f if ctx.bb_pct_b else 'N/A'}

## Geopolitical Risk Events
- Active events: {geo_events_str}

## Required Response Format (JSON only, no extra text)
{{
  "action": "buy" | "sell" | "hold",
  "confidence": 0.00-1.00,
  "reasoning": "2-3 sentence explanation referencing specific data points",
  "key_risks": ["risk1", "risk2"],
  "suggested_position_size": 0.00-0.10
}}"""


def get_system_prompt() -> str:
    return _SYSTEM_PROMPT
