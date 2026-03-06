"""Unit tests for the Claude prompt builder.

Task S3-T1-002 acceptance criteria.
"""

from datetime import date
from analysis.indicators import IndicatorSnapshot
from claude.prompt_builder import build_prompt, AnalysisContext


def _ctx(**overrides) -> AnalysisContext:
    defaults = dict(
        ticker="SPY",
        close_price=480.0,
        technical_score=62.0,
        sentiment_score=0.15,
        geo_risk_score=20.0,
        composite_score=58.0,
        rsi=48.0,
        macd=1.2,
        macd_hist=0.3,
        bb_pct_b=0.55,
        triggered_geo_events=[],
        previous_composite=55.0,
        as_of_date=date(2024, 1, 10),
    )
    defaults.update(overrides)
    return AnalysisContext(**defaults)


def test_prompt_contains_ticker():
    prompt = build_prompt(_ctx())
    assert "SPY" in prompt


def test_prompt_contains_scores():
    prompt = build_prompt(_ctx(composite_score=72.5))
    assert "72.5" in prompt


def test_prompt_contains_json_format():
    prompt = build_prompt(_ctx())
    assert '"action"' in prompt
    assert '"confidence"' in prompt
    assert '"reasoning"' in prompt


def test_prompt_under_token_limit():
    # Rough token estimate: ~4 chars per token
    prompt = build_prompt(_ctx())
    estimated_tokens = len(prompt) / 4
    assert estimated_tokens < 2000, f"Prompt too long: ~{estimated_tokens:.0f} tokens"


def test_prompt_shows_delta_trend():
    prompt = build_prompt(_ctx(composite_score=70.0, previous_composite=55.0))
    assert "up" in prompt.lower()


def test_prompt_geo_events_shown():
    prompt = build_prompt(_ctx(triggered_geo_events=["war_conflict", "sanctions"]))
    assert "war_conflict" in prompt


def test_prompt_no_previous_score():
    ctx = _ctx(previous_composite=None)
    prompt = build_prompt(ctx)
    assert "SPY" in prompt  # should still build without previous score
