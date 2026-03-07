"""Claude API client — multi-turn (3 turns) with retry and usage recording.

Turn 1: market signals analysis
Turn 2: risk assessment
Turn 3: final JSON recommendation
"""

from __future__ import annotations

import anthropic
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from claude.prompt_builder import (
    build_turn1_prompt,
    build_turn2_prompt,
    build_turn3_prompt,
    get_system_prompt,
    AnalysisContext,
)
from claude.usage_tracker import record_usage

log = structlog.get_logger()

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


class ClaudeAPIError(Exception):
    pass


@retry(
    retry=retry_if_exception_type(anthropic.RateLimitError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
)
def _call_api(
    messages: list[dict],
    max_tokens: int = 512,
) -> anthropic.types.Message:
    """Raw API call with retry on rate limit."""
    return _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=get_system_prompt(),
        messages=messages,
    )


def get_recommendation(ctx: AnalysisContext) -> str:
    """
    Run a 3-turn conversation with Claude for the given symbol.

    Turn 1 — market signals context
    Turn 2 — risk assessment
    Turn 3 — final JSON recommendation (this is the return value)

    Returns the raw response text from turn 3.
    Raises ClaudeAPIError on unrecoverable failure.
    """
    log.info("claude.multi_turn.start", ticker=ctx.ticker, model=CLAUDE_MODEL)

    total_input = 0
    total_output = 0

    # Build conversation history incrementally
    messages: list[dict] = []

    try:
        # ── Turn 1: signal analysis ──────────────────────────────────────────
        messages.append({"role": "user", "content": build_turn1_prompt(ctx)})
        r1 = _call_api(messages, max_tokens=300)
        turn1_text = r1.content[0].text
        total_input  += r1.usage.input_tokens
        total_output += r1.usage.output_tokens
        messages.append({"role": "assistant", "content": turn1_text})
        log.debug("claude.turn1_done", ticker=ctx.ticker, tokens=r1.usage.output_tokens)

        # ── Turn 2: risk assessment ──────────────────────────────────────────
        messages.append({"role": "user", "content": build_turn2_prompt(ctx)})
        r2 = _call_api(messages, max_tokens=300)
        turn2_text = r2.content[0].text
        total_input  += r2.usage.input_tokens
        total_output += r2.usage.output_tokens
        messages.append({"role": "assistant", "content": turn2_text})
        log.debug("claude.turn2_done", ticker=ctx.ticker, tokens=r2.usage.output_tokens)

        # ── Turn 3: final JSON recommendation ───────────────────────────────
        messages.append({"role": "user", "content": build_turn3_prompt(ctx)})
        r3 = _call_api(messages, max_tokens=512)
        final_text = r3.content[0].text
        total_input  += r3.usage.input_tokens
        total_output += r3.usage.output_tokens
        log.debug("claude.turn3_done", ticker=ctx.ticker, tokens=r3.usage.output_tokens)

    except anthropic.AuthenticationError as exc:
        raise ClaudeAPIError(f"Claude auth failed: {exc}") from exc
    except anthropic.RateLimitError as exc:
        raise ClaudeAPIError(f"Claude rate limit exhausted after retries: {exc}") from exc
    except anthropic.APIError as exc:
        raise ClaudeAPIError(f"Claude API error: {exc}") from exc

    record_usage(
        input_tokens=total_input,
        output_tokens=total_output,
        symbol=ctx.ticker,
        trigger_reason="multi_turn_analysis",
    )
    log.info(
        "claude.multi_turn.complete",
        ticker=ctx.ticker,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
    )

    return final_text
