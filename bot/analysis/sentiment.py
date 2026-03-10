"""Sentiment analysis engine — uses FinBERT for financial news.

Task S2-T2-001
Falls back to a lexicon-based scorer when the transformer model is unavailable
(e.g. in CI / lightweight environments).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()

# ── FinBERT loader (lazy, so the bot starts even without torch) ────────────

_pipeline = None  # cached transformers pipeline


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from transformers import pipeline as hf_pipeline
        _pipeline = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            top_k=None,
        )
        log.info("sentiment.finbert_loaded")
    except Exception as exc:
        log.warning("sentiment.finbert_unavailable", reason=str(exc))
        _pipeline = None
    return _pipeline


# ── Fallback lexicon (simple but fast) ────────────────────────────────────

_POSITIVE = {
    "surges", "beats", "record", "growth", "profit", "revenue", "upgrade",
    "buy", "bullish", "strong", "gains", "rally", "outperform", "positive",
    "soars", "rises", "breakthrough", "innovation", "dividend",
}
_NEGATIVE = {
    "drops", "misses", "loss", "decline", "downgrade", "sell", "bearish",
    "weak", "falls", "crash", "lawsuit", "layoffs", "recall", "fraud",
    "bankruptcy", "cut", "disappoints", "plunges", "warning", "concern",
}


def _lexicon_score(text: str) -> float:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos = len(words & _POSITIVE)
    neg = len(words & _NEGATIVE)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)


# ── Core scoring ───────────────────────────────────────────────────────────

@dataclass
class ArticleScore:
    headline: str
    score: float   # -1.0 (negative) to +1.0 (positive)
    method: str    # "finbert" | "lexicon"


def score_text(text: str) -> ArticleScore:
    """Score a single piece of text. Returns ArticleScore."""
    pipe = _get_pipeline()
    if pipe is not None:
        try:
            results = pipe(text[:512], truncation=True)[0]  # top_k returns list
            label_scores = {r["label"].lower(): r["score"] for r in results}
            score = label_scores.get("positive", 0.0) - label_scores.get("negative", 0.0)
            return ArticleScore(headline=text, score=round(score, 4), method="finbert")
        except Exception as exc:
            log.warning("sentiment.finbert_error", error=str(exc))

    return ArticleScore(headline=text, score=_lexicon_score(text), method="lexicon")


def compute_sentiment_score(
    ticker: str,
    hours_back: int = 24,
) -> Optional[float]:
    """
    Aggregate sentiment score for *ticker* over recent news.
    Returns a value in [-1.0, +1.0], or None if no news found.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)

    session = get_session()
    try:
        rows = session.execute(
            text("""
                SELECT ni.headline, ni.summary
                FROM   news_items ni
                JOIN   news_symbols ns ON ns.news_id = ni.id
                JOIN   symbols s       ON s.id = ns.symbol_id
                WHERE  s.ticker      = :ticker
                  AND  ni.published_at >= :since
                ORDER  BY ni.published_at DESC
                LIMIT  50
            """),
            {"ticker": ticker, "since": since},
        ).fetchall()
    finally:
        session.close()

    if not rows:
        log.info("sentiment.no_news", ticker=ticker)
        return None

    scores = []
    for headline, summary in rows:
        combined = f"{headline}. {summary or ''}".strip()
        article = score_text(combined)
        scores.append(article.score)

    avg = round(sum(scores) / len(scores), 4)
    log.info("sentiment.computed", ticker=ticker, articles=len(scores), score=avg)
    return avg
