"""Tests for bot/claude/portfolio_prompt.py — Phase 3 Sprint 1"""

import pytest
from unittest.mock import patch, MagicMock

from claude.portfolio_prompt import (
    PortfolioPromptBuilder, PortfolioSnapshot, PeerContext
)
from claude.prompt_builder import AnalysisContext


# ── Helpers ────────────────────────────────────────────────────────────────

def _ctx(**kwargs) -> AnalysisContext:
    return AnalysisContext(
        ticker=kwargs.get("ticker", "AAPL"),
        technical_score=kwargs.get("technical_score", 65.0),
        sentiment_score=kwargs.get("sentiment_score", 60.0),
        geo_risk_score=kwargs.get("geo_risk_score", 30.0),
        composite_score=kwargs.get("composite_score", 62.0),
        close_price=kwargs.get("close_price", 175.0),
        rsi=kwargs.get("rsi", 52.0),
        macd=kwargs.get("macd", 0.35),
        analysis_date=kwargs.get("analysis_date", "2026-03-07"),
        asset_type=kwargs.get("asset_type", "stock"),
    )


def _snapshot(**kwargs) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_value=kwargs.get("portfolio_value", 100_000),
        cash=kwargs.get("cash", 20_000),
        equity=kwargs.get("equity", 80_000),
        day_pl=kwargs.get("day_pl", 500),
        positions=kwargs.get("positions", []),
    )


def _builder_with_empty_db() -> PortfolioPromptBuilder:
    builder = PortfolioPromptBuilder()
    return builder


# ── PortfolioPromptBuilder.build ────────────────────────────────────────────

class TestBuild:
    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_returns_non_empty_string(self, _, __):
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx())
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_contains_ticker(self, _, __):
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx(ticker="NVDA"))
        assert "NVDA" in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_contains_scores(self, _, __):
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx(composite_score=71.5))
        assert "71.5" in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_portfolio_section_included(self, _, __):
        builder = _builder_with_empty_db()
        snap = _snapshot(portfolio_value=100_000, cash=25_000)
        prompt = builder.build(_ctx(), portfolio=snap)
        assert "Portfolio" in prompt
        assert "25,000" in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_portfolio_none_skips_section(self, _, __):
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx(), portfolio=None)
        assert "Total value" not in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history")
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_history_section_included(self, _, mock_hist):
        mock_hist.return_value = [
            {"action": "buy", "confidence": 0.8, "source": "claude", "created_at": "2026-03-01T12:00:00"}
        ]
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx())
        assert "Recent Recommendations" in prompt
        assert "buy" in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context")
    def test_peer_section_included(self, mock_peer, _):
        mock_peer.return_value = PeerContext("AAPL", 65.0, 2, 6)
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx())
        assert "Peer Context" in prompt
        assert "#2 of 6" in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_output_schema_always_present(self, _, __):
        builder = _builder_with_empty_db()
        prompt = builder.build(_ctx())
        assert "Required JSON Output" in prompt
        assert '"action"' in prompt
        assert '"tags"' in prompt

    @patch.object(PortfolioPromptBuilder, "_fetch_history", return_value=[])
    @patch.object(PortfolioPromptBuilder, "_fetch_peer_context", return_value=None)
    def test_prompt_under_character_limit(self, _, __):
        builder = _builder_with_empty_db()
        snap = _snapshot(positions=[
            {"symbol": f"SYM{i}", "qty": 10, "mkt_value": 1000, "unrealised_pl": 50}
            for i in range(20)   # lots of positions to stress-test truncation
        ])
        prompt = builder.build(_ctx(), portfolio=snap)
        assert len(prompt) <= 7_200   # slight buffer over _MAX_PROMPT_CHARS


# ── get_system_prompt ───────────────────────────────────────────────────────

class TestSystemPrompt:
    def test_returns_string(self):
        sp = PortfolioPromptBuilder.get_system_prompt()
        assert isinstance(sp, str)
        assert len(sp) > 50

    def test_mentions_capital_preservation(self):
        sp = PortfolioPromptBuilder.get_system_prompt()
        assert "capital" in sp.lower()

    def test_mentions_position_size_limit(self):
        sp = PortfolioPromptBuilder.get_system_prompt()
        assert "10%" in sp


# ── Static section helpers ──────────────────────────────────────────────────

class TestSectionHelpers:
    def test_scores_section_contains_composite(self):
        ctx = _ctx(composite_score=77.3)
        section = PortfolioPromptBuilder._scores_section(ctx)
        assert "77.3" in section

    def test_portfolio_section_shows_cash_pct(self):
        snap = _snapshot(portfolio_value=100_000, cash=20_000)
        section = PortfolioPromptBuilder._portfolio_section(snap)
        assert "20.0%" in section

    def test_portfolio_section_limits_positions_to_8(self):
        positions = [{"symbol": f"S{i}", "qty": 10, "mkt_value": 1000, "unrealised_pl": 0} for i in range(15)]
        snap = _snapshot(positions=positions)
        section = PortfolioPromptBuilder._portfolio_section(snap)
        # Only first 8 should appear
        count = section.count("mkt=$")
        assert count <= 8

    def test_output_schema_valid_json_skeleton(self):
        schema = PortfolioPromptBuilder._output_schema()
        assert '"action"' in schema
        assert '"confidence"' in schema
        assert '"position_size"' in schema
        assert '"tags"' in schema
