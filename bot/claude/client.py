"""Claude API client with retry, error handling, and usage recording.

Task S3-T1-001
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
from claude.prompt_builder import build_prompt, get_system_prompt, AnalysisContext
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
def _call_api(prompt: str, max_tokens: int = 512) -> anthropic.types.Message:
    """Raw API call with retry on rate limit."""
    client = _get_client()
    return client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=get_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
    )


def get_recommendation(ctx: AnalysisContext) -> str:
    """
    Call Claude with the given analysis context.
    Returns the raw response text.
    Raises ClaudeAPIError on unrecoverable failure.
    """
    prompt = build_prompt(ctx)
    log.info("claude.calling", ticker=ctx.ticker, model=CLAUDE_MODEL)

    try:
        response = _call_api(prompt)
        text = response.content[0].text

        record_usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            symbol=ctx.ticker,
            trigger_reason="analysis_pipeline",
        )
        log.info(
            "claude.response_received",
            ticker=ctx.ticker,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return text

    except anthropic.AuthenticationError as exc:
        raise ClaudeAPIError(f"Claude auth failed: {exc}") from exc
    except anthropic.RateLimitError as exc:
        raise ClaudeAPIError(f"Claude rate limit exhausted after retries: {exc}") from exc
    except anthropic.APIError as exc:
        raise ClaudeAPIError(f"Claude API error: {exc}") from exc
