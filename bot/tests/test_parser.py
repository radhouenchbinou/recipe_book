"""Unit tests for the Claude response parser.

Task S3-T2-001 acceptance criteria.
"""

import pytest
from claude.parser import parse_response, _extract_json, VALID_ACTIONS


# ── JSON extraction ────────────────────────────────────────────────────────

def test_extract_plain_json():
    raw = '{"action": "buy", "confidence": 0.8, "reasoning": "Strong momentum.", "key_risks": [], "suggested_position_size": 0.05}'
    data = _extract_json(raw)
    assert data["action"] == "buy"


def test_extract_json_from_markdown_fence():
    raw = '```json\n{"action": "sell", "confidence": 0.7, "reasoning": "Bearish.", "key_risks": [], "suggested_position_size": 0.0}\n```'
    data = _extract_json(raw)
    assert data["action"] == "sell"


def test_extract_json_raises_on_no_json():
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("Sorry, I cannot provide financial advice.")


# ── parse_response ─────────────────────────────────────────────────────────

def test_parse_buy_recommendation():
    raw = '{"action": "buy", "confidence": 0.82, "reasoning": "RSI oversold, MACD bullish.", "key_risks": ["volatility"], "suggested_position_size": 0.07}'
    rec = parse_response(raw)
    assert rec.action == "buy"
    assert rec.confidence == 0.82
    assert rec.source == "claude"
    assert len(rec.key_risks) == 1


def test_parse_clamps_confidence():
    raw = '{"action": "hold", "confidence": 1.5, "reasoning": "x", "key_risks": [], "suggested_position_size": 0.05}'
    rec = parse_response(raw)
    assert rec.confidence == 1.0


def test_parse_clamps_position_size():
    raw = '{"action": "buy", "confidence": 0.9, "reasoning": "x", "key_risks": [], "suggested_position_size": 0.50}'
    rec = parse_response(raw)
    assert rec.suggested_position_size == 0.10


def test_parse_invalid_action_defaults_hold():
    raw = '{"action": "strong_buy", "confidence": 0.9, "reasoning": "x", "key_risks": [], "suggested_position_size": 0.05}'
    rec = parse_response(raw)
    assert rec.action == "hold"


def test_parse_truncates_reasoning():
    long_reasoning = "x" * 2000
    raw = f'{{"action": "hold", "confidence": 0.5, "reasoning": "{long_reasoning}", "key_risks": [], "suggested_position_size": 0.0}}'
    rec = parse_response(raw)
    assert len(rec.reasoning) <= 1000


# ── All valid actions parsed correctly ───────────────────────────────────

@pytest.mark.parametrize("action", ["buy", "sell", "hold"])
def test_all_valid_actions(action):
    raw = f'{{"action": "{action}", "confidence": 0.7, "reasoning": "test", "key_risks": [], "suggested_position_size": 0.05}}'
    rec = parse_response(raw)
    assert rec.action == action
    assert rec.action in VALID_ACTIONS
