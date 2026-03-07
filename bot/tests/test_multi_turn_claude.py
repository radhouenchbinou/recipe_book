"""Tests for multi-turn Claude client."""

from datetime import date
from unittest.mock import MagicMock, patch, call

import pytest

from claude.prompt_builder import AnalysisContext, build_turn1_prompt, build_turn2_prompt, build_turn3_prompt


def _make_ctx(**kwargs) -> AnalysisContext:
    defaults = dict(
        ticker="AAPL",
        close_price=185.50,
        technical_score=72.0,
        sentiment_score=0.35,
        geo_risk_score=25.0,
        composite_score=68.0,
        fundamental_score=75.0,
        rsi=58.0,
        macd=0.45,
        macd_hist=0.12,
        bb_pct_b=0.65,
        triggered_geo_events=[],
        previous_composite=65.0,
        as_of_date=date(2026, 3, 7),
    )
    defaults.update(kwargs)
    return AnalysisContext(**defaults)


class TestPromptBuilder:
    def test_turn1_includes_data_block(self):
        ctx = _make_ctx()
        prompt = build_turn1_prompt(ctx)
        assert "AAPL" in prompt
        assert "185.50" in prompt
        assert "72.0" in prompt  # technical score

    def test_turn2_is_follow_up(self):
        ctx = _make_ctx()
        prompt = build_turn2_prompt(ctx)
        assert "AAPL" in prompt
        assert "risk" in prompt.lower()

    def test_turn3_requests_json(self):
        ctx = _make_ctx()
        prompt = build_turn3_prompt(ctx)
        assert "action" in prompt
        assert "confidence" in prompt
        assert "JSON" in prompt

    def test_fundamental_score_included_in_turn1(self):
        ctx = _make_ctx(fundamental_score=80.0)
        prompt = build_turn1_prompt(ctx)
        assert "80.0" in prompt

    def test_fundamental_unavailable_shown_in_turn1(self):
        ctx = _make_ctx(fundamental_score=None)
        prompt = build_turn1_prompt(ctx)
        assert "unavailable" in prompt

    def test_geo_events_shown(self):
        ctx = _make_ctx(triggered_geo_events=["Middle East conflict", "Tariff escalation"])
        prompt = build_turn1_prompt(ctx)
        assert "Middle East conflict" in prompt


class TestMultiTurnClient:
    """Integration-style test: verify 3 API calls are made per recommendation."""

    def _make_message(self, text: str) -> MagicMock:
        msg = MagicMock()
        msg.content = [MagicMock()]
        msg.content[0].text = text
        msg.usage.input_tokens = 100
        msg.usage.output_tokens = 50
        return msg

    def test_three_turns_called(self):
        ctx = _make_ctx()
        json_response = '{"action": "hold", "confidence": 0.55, "reasoning": "Mixed signals.", "key_risks": [], "suggested_position_size": 0.0}'

        with patch("claude.client._call_api") as mock_api, \
             patch("claude.client.record_usage") as _mock_usage:

            mock_api.side_effect = [
                self._make_message("Turn 1 analysis: RSI at 58 indicates neutral momentum."),
                self._make_message("Turn 2 risks: geopolitical tensions could weigh on sentiment."),
                self._make_message(json_response),
            ]

            from claude.client import get_recommendation
            result = get_recommendation(ctx)

        assert mock_api.call_count == 3
        assert result == json_response

    def test_conversation_grows_between_turns(self):
        """Each turn's messages list must include prior turns."""
        ctx = _make_ctx()
        captured_calls = []

        def _fake_call(messages, **kwargs):
            captured_calls.append(list(messages))  # snapshot
            msg = MagicMock()
            msg.content = [MagicMock()]
            msg.content[0].text = f"Response {len(messages)}"
            msg.usage.input_tokens = 10
            msg.usage.output_tokens = 10
            return msg

        with patch("claude.client._call_api", side_effect=_fake_call), \
             patch("claude.client.record_usage"):
            from claude.client import get_recommendation
            get_recommendation(ctx)

        assert len(captured_calls[0]) == 1    # Turn 1: [user]
        assert len(captured_calls[1]) == 3    # Turn 2: [user, assistant, user]
        assert len(captured_calls[2]) == 5    # Turn 3: [u, a, u, a, u]
