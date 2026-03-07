"""Advanced Claude prompt builder with portfolio context.

Phase 3 / Sprint 1
Extends the base prompt builder to include:
  - Full portfolio snapshot (positions, cash, total equity)
  - Recent recommendation history for the symbol (last 5)
  - Peer comparison (relative score vs other tracked symbols)
  - Tags for classification of the recommendation
All while staying under the 2000-token target.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session
from claude.prompt_builder import AnalysisContext

log = structlog.get_logger()

_MAX_HISTORY      = 5
_MAX_PROMPT_CHARS = 7_000   # ~1 750 tokens with GPT-4 tokenisation


@dataclass
class PortfolioSnapshot:
    portfolio_value: float
    cash: float
    equity: float
    day_pl: float
    positions: list[dict] = field(default_factory=list)   # {symbol, qty, mkt_value, unrealised_pl}


@dataclass
class PeerContext:
    symbol: str
    composite_score: float
    rank: int     # rank among all tracked symbols (1 = highest)
    total: int    # total number of tracked symbols


class PortfolioPromptBuilder:
    """
    Builds a rich, portfolio-aware prompt for Claude recommendations.

    The resulting prompt includes:
    - Symbol technical / sentiment / geo scores (from AnalysisContext)
    - Current portfolio composition and cash position
    - Last N recommendations for this symbol
    - Relative ranking vs peer symbols
    - JSON output schema (same as base prompt_builder)
    """

    def build(
        self,
        ctx: AnalysisContext,
        portfolio: Optional[PortfolioSnapshot] = None,
        estimated_tokens: int = 1_800,
    ) -> str:
        """
        Build the advanced prompt string.

        Args:
            ctx: Base analysis context (scores, market data).
            portfolio: Optional live portfolio snapshot.
            estimated_tokens: Soft token budget (controls history truncation).

        Returns:
            Prompt string ready for Claude.
        """
        history  = self._fetch_history(ctx.ticker)
        peers    = self._fetch_peer_context(ctx.ticker)

        sections = [
            self._header(ctx),
            self._scores_section(ctx),
            self._portfolio_section(portfolio) if portfolio else "",
            self._peers_section(peers) if peers else "",
            self._history_section(history) if history else "",
            self._output_schema(),
        ]

        prompt = "\n\n".join(s for s in sections if s)

        # Trim if over hard character limit
        if len(prompt) > _MAX_PROMPT_CHARS:
            prompt = prompt[:_MAX_PROMPT_CHARS] + "\n\n[...truncated for length]"

        log.debug("portfolio_prompt.built", ticker=ctx.ticker, chars=len(prompt))
        return prompt

    @staticmethod
    def get_system_prompt() -> str:
        return (
            "You are a disciplined, risk-aware quantitative trading analyst. "
            "You have access to technical indicators, sentiment scores, geopolitical risk data, "
            "the current portfolio composition, and historical recommendation performance. "
            "Prioritise capital preservation. Never recommend more than 10% position size. "
            "Your response must be valid JSON only — no markdown, no commentary outside the JSON object."
        )

    # ── Prompt sections ──────────────────────────────────────────────────────

    @staticmethod
    def _header(ctx: AnalysisContext) -> str:
        return (
            f"## Trading Analysis Request: {ctx.ticker}\n"
            f"Date: {ctx.analysis_date}\n"
            f"Asset class: {ctx.asset_type or 'equity'}"
        )

    @staticmethod
    def _scores_section(ctx: AnalysisContext) -> str:
        lines = [
            "## Analysis Scores (0–100)",
            f"- Technical:  {ctx.technical_score:.1f}  (RSI/MACD/Bollinger composite)",
            f"- Sentiment:  {ctx.sentiment_score:.1f}  (FinBERT + news volume)",
            f"- Geo Risk:   {ctx.geo_risk_score:.1f}  (geopolitical event severity)",
            f"- Composite:  {ctx.composite_score:.1f}  (40% tech + 35% sentiment + 25% geo)",
        ]
        if ctx.close_price:
            lines.append(f"\nLatest close: ${ctx.close_price:.2f}")
        if ctx.rsi is not None:
            lines.append(f"RSI (14):     {ctx.rsi:.1f}")
        if ctx.macd is not None:
            lines.append(f"MACD:         {ctx.macd:.4f}")
        return "\n".join(lines)

    @staticmethod
    def _portfolio_section(p: PortfolioSnapshot) -> str:
        lines = [
            "## Current Portfolio",
            f"- Total value: ${p.portfolio_value:,.0f}",
            f"- Cash:        ${p.cash:,.0f}  ({p.cash/p.portfolio_value*100:.1f}% of portfolio)" if p.portfolio_value else f"- Cash: ${p.cash:,.0f}",
            f"- Day P&L:     ${p.day_pl:+,.0f}",
        ]
        if p.positions:
            lines.append("\nOpen positions:")
            for pos in p.positions[:8]:   # cap at 8 to stay under token limit
                lines.append(
                    f"  {pos.get('symbol','?'):6} "
                    f"qty={pos.get('qty',0):4}  "
                    f"mkt=${pos.get('mkt_value',0):>10,.0f}  "
                    f"P&L=${pos.get('unrealised_pl',0):>+8,.0f}"
                )
        return "\n".join(lines)

    @staticmethod
    def _peers_section(peer: PeerContext) -> str:
        return (
            f"## Peer Context\n"
            f"{peer.symbol} ranks #{peer.rank} of {peer.total} tracked symbols "
            f"by composite score ({peer.composite_score:.1f})."
        )

    @staticmethod
    def _history_section(history: list[dict]) -> str:
        if not history:
            return ""
        lines = ["## Recent Recommendations (newest first)"]
        for h in history:
            lines.append(
                f"  {h.get('created_at','?')[:10]}  "
                f"action={h.get('action','?'):4}  "
                f"confidence={h.get('confidence',0):.2f}  "
                f"source={h.get('source','?')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _output_schema() -> str:
        return (
            '## Required JSON Output\n'
            'Respond with ONLY this JSON object:\n'
            '{\n'
            '  "action":        "buy" | "sell" | "hold",\n'
            '  "confidence":    0.0–1.0,\n'
            '  "position_size": 0.0–0.10,\n'
            '  "rationale":     "one sentence explanation",\n'
            '  "tags":          ["tag1", "tag2"]  // e.g. ["momentum", "earnings"]\n'
            '}'
        )

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _fetch_history(self, ticker: str) -> list[dict]:
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT r.action, r.confidence, r.source, r.created_at
                    FROM recommendations r
                    JOIN symbols s ON s.id = r.symbol_id
                    WHERE s.ticker = :ticker
                    ORDER BY r.created_at DESC
                    LIMIT :limit
                """),
                {"ticker": ticker, "limit": _MAX_HISTORY},
            ).fetchall()
        finally:
            session.close()
        return [{"action": r[0], "confidence": float(r[1] or 0),
                 "source": r[2], "created_at": str(r[3])} for r in rows]

    def _fetch_peer_context(self, ticker: str) -> Optional[PeerContext]:
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT s.ticker, a.composite_score
                    FROM analysis_scores a
                    JOIN symbols s ON s.id = a.symbol_id
                    WHERE a.scored_at = (
                        SELECT MAX(a2.scored_at) FROM analysis_scores a2
                        WHERE a2.symbol_id = a.symbol_id
                    )
                    ORDER BY a.composite_score DESC
                """)
            ).fetchall()
        finally:
            session.close()

        if not rows:
            return None
        tickers = [r[0] for r in rows]
        scores  = {r[0]: float(r[1]) for r in rows}
        try:
            rank = tickers.index(ticker) + 1
        except ValueError:
            return None
        return PeerContext(
            symbol=ticker,
            composite_score=scores.get(ticker, 0),
            rank=rank,
            total=len(tickers),
        )
