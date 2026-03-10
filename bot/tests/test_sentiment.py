"""Unit tests for the sentiment analysis engine.

Task S2-T2-001 acceptance criteria.
"""

from unittest.mock import MagicMock, patch

from analysis.sentiment import score_text, _lexicon_score, _POSITIVE, _NEGATIVE


# ── Lexicon scorer ─────────────────────────────────────────────────────────

def test_lexicon_positive():
    score = _lexicon_score("Apple surges to record revenue growth beats expectations")
    assert score > 0.0


def test_lexicon_negative():
    score = _lexicon_score("Stock drops after earnings miss and revenue decline")
    assert score < 0.0


def test_lexicon_neutral():
    score = _lexicon_score("The company announced its quarterly results today")
    assert score == 0.0


def test_lexicon_range():
    for _ in range(20):
        import random
        words = random.choices(list(_POSITIVE | _NEGATIVE), k=5)
        score = _lexicon_score(" ".join(words))
        assert -1.0 <= score <= 1.0


# ── score_text falls back to lexicon when FinBERT unavailable ─────────────

@patch("analysis.sentiment._get_pipeline", return_value=None)
def test_score_text_fallback_positive(mock_pipe):
    result = score_text("Company surges to record profits growth beats all estimates")
    assert result.method == "lexicon"
    assert result.score > 0.0


@patch("analysis.sentiment._get_pipeline", return_value=None)
def test_score_text_fallback_negative(mock_pipe):
    result = score_text("Stock plunges after massive loss and bankruptcy warning")
    assert result.method == "lexicon"
    assert result.score < 0.0


# ── compute_sentiment_score aggregation ───────────────────────────────────

@patch("analysis.sentiment.get_session")
@patch("analysis.sentiment._get_pipeline", return_value=None)
def test_compute_sentiment_no_news(mock_pipe, mock_session):
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = []
    mock_session.return_value = session

    from analysis.sentiment import compute_sentiment_score
    result = compute_sentiment_score("AAPL")
    assert result is None


@patch("analysis.sentiment.get_session")
@patch("analysis.sentiment._get_pipeline", return_value=None)
def test_compute_sentiment_aggregates(mock_pipe, mock_session):
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = [
        ("Apple surges record growth", "Strong earnings beat"),
        ("Apple drops on concerns", "Weak guidance disappoints"),
        ("Apple unveils new product", None),
    ]
    mock_session.return_value = session

    from analysis.sentiment import compute_sentiment_score
    result = compute_sentiment_score("AAPL")
    assert result is not None
    assert -1.0 <= result <= 1.0
