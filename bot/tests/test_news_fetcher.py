"""Unit tests for the news fetcher.

Task S1-T2-002 acceptance criteria.
"""

from unittest.mock import MagicMock, patch


@patch("collectors.news_fetcher.get_session")
@patch("collectors.news_fetcher.feedparser.parse")
def test_fetch_news_saves_articles(mock_parse, mock_session):
    mock_parse.return_value = MagicMock(
        feed={"title": "Yahoo Finance"},
        entries=[
            MagicMock(
                title="Apple hits all-time high",
                summary="Apple stock surges after earnings.",
                link="https://example.com/1",
                published_parsed=(2024, 1, 10, 12, 0, 0, 0, 0, 0),
                id="entry-1",
                tags=[],
            )
        ],
    )

    session = MagicMock()
    session.execute.return_value.fetchone.return_value = ("fake-uuid",)
    mock_session.return_value = session

    from collectors.news_fetcher import fetch_news

    count = fetch_news(feeds=["http://fake-feed.example.com"])
    assert count == 1
    session.commit.assert_called_once()


@patch("collectors.news_fetcher.get_session")
@patch("collectors.news_fetcher.feedparser.parse")
def test_fetch_news_skips_empty_headlines(mock_parse, mock_session):
    mock_parse.return_value = MagicMock(
        feed={"title": "Reuters"},
        entries=[MagicMock(title="", summary=None, link=None, published_parsed=None, id=None, tags=[])],
    )
    session = MagicMock()
    mock_session.return_value = session

    from collectors.news_fetcher import fetch_news

    count = fetch_news(feeds=["http://fake-feed.example.com"])
    assert count == 0


def test_detect_symbols():
    from collectors.news_fetcher import _detect_symbols

    symbols = _detect_symbols("Apple announces new iPhone, Microsoft sees NVDA GPU demand")
    assert "AAPL" in symbols
    assert "MSFT" in symbols
    assert "NVDA" in symbols
