"""Builds multi-turn prompts for the 3-turn Claude conversation.

Turn 1: market signals analysis
Turn 2: risk assessment
Turn 3: final JSON recommendation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class AnalysisContext:
    ticker: str
    close_price: float
    technical_score: float           # 0-100
    sentiment_score: Optional[float]  # -1 to +1
    geo_risk_score: float            # 0-100
    composite_score: float           # 0-100
    fundamental_score: Optional[float]  # 0-100 (None if unavailable)
    rsi: Optional[float]
    macd: Optional[float]
    macd_hist: Optional[float]
    bb_pct_b: Optional[float]
    triggered_geo_events: list[str]
    previous_composite: Optional[float]
    as_of_date: date


_SYSTEM_PROMPT = """You are a quantitative trading analyst AI. Your role is to provide
concise, data-driven buy/sell/hold recommendations for US equities and ETFs.

Rules:
- Base decisions ONLY on the data provided
- Account for geopolitical risk as a downside factor
- Consider technical momentum, fundamentals, and market sentiment together
- Be conservative: only recommend 'buy' or 'sell' when confidence >= 0.65
- Default to 'hold' when signals are mixed or insufficient
- Never recommend more than 10% position size
- Paper trading context: recommendations are for simulation only"""


def _data_block(ctx: AnalysisContext) -> str:
    """Shared data block used across all 3 turns."""
    delta_str = ""
    if ctx.previous_composite is not None:
        delta = ctx.composite_score - ctx.previous_composite
        delta_str = f"\n- Score trend: {'↑' if delta > 0 else '↓'} {abs(delta):.1f} pts"

    fundamental_str = (
        f"{ctx.fundamental_score:.1f}/100" if ctx.fundamental_score is not None else "unavailable"
    )
    sentiment_str = (
        f"{ctx.sentiment_score:+.3f}" if ctx.sentiment_score is not None else "unavailable"
    )
    geo_events_str = (
        ", ".join(ctx.triggered_geo_events) if ctx.triggered_geo_events else "none detected"
    )

    return f"""Ticker: {ctx.ticker} | Price: ${ctx.close_price:.2f} | Date: {ctx.as_of_date}

Scores (0-100, higher = more bullish):
- Technical:    {ctx.technical_score:.1f}
- Fundamental:  {fundamental_str}
- Sentiment:    {sentiment_str} (range: -1 to +1)
- Geo risk:     {ctx.geo_risk_score:.1f} (higher = riskier)
- Composite:    {ctx.composite_score:.1f}{delta_str}

Indicators:
- RSI-14: {ctx.rsi:.1f if ctx.rsi is not None else 'N/A'}
- MACD: {ctx.macd:.4f if ctx.macd is not None else 'N/A'}
- MACD histogram: {ctx.macd_hist:.4f if ctx.macd_hist is not None else 'N/A'}
- Bollinger %B: {ctx.bb_pct_b:.3f if ctx.bb_pct_b is not None else 'N/A'}

Geo events: {geo_events_str}"""


def build_turn1_prompt(ctx: AnalysisContext) -> str:
    """Turn 1 — ask Claude to summarise the key technical + fundamental signals."""
    return f"""Analyse the following data for {ctx.ticker} and summarise the 2-3 most
significant technical and fundamental signals (3-4 sentences, no JSON yet).

{_data_block(ctx)}"""


def build_turn2_prompt(ctx: AnalysisContext) -> str:
    """Turn 2 — ask Claude to identify the primary risks given the prior analysis."""
    return (
        "Given your signal analysis above, identify the 2-3 primary risks that could "
        "invalidate a bullish or bearish thesis for "
        f"{ctx.ticker}. Be specific and concise (3-4 sentences, no JSON yet)."
    )


def build_turn3_prompt(ctx: AnalysisContext) -> str:
    """Turn 3 — ask Claude for the final JSON recommendation."""
    return """Based on your signal analysis and risk assessment above, provide the final
trading recommendation in this exact JSON format (JSON only, no extra text):

{
  "action": "buy" | "sell" | "hold",
  "confidence": 0.00-1.00,
  "reasoning": "2-3 sentence explanation referencing specific data points",
  "key_risks": ["risk1", "risk2"],
  "suggested_position_size": 0.00-0.10
}"""


def get_system_prompt() -> str:
    return _SYSTEM_PROMPT
