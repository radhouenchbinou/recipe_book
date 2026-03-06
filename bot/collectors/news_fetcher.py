"""News collector — fetches from RSS feeds and persists to DB.

Task S1-T2-002
"""

from datetime import datetime, timezone
from typing import Optional
import feedparser
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()

RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY,QQQ,GLD,AAPL,MSFT,NVDA&region=US&lang=en-US",
    "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
]

_INSERT_NEWS = """
INSERT INTO news_items (headline, summary, source, url, published_at, raw_json)
VALUES (:headline, :summary, :source, :url, :published_at, :raw_json::jsonb)
ON CONFLICT DO NOTHING
RETURNING id
"""

_LINK_SYMBOL = """
INSERT INTO news_symbols (news_id, symbol_id)
SELECT :news_id, s.id
FROM   symbols s
WHERE  s.ticker = :ticker
ON CONFLICT DO NOTHING
"""

# Simple keyword → symbol mapping for tagging
SYMBOL_KEYWORDS: dict[str, list[str]] = {
    "AAPL": ["apple", "aapl", "iphone", "tim cook"],
    "MSFT": ["microsoft", "msft", "azure", "copilot"],
    "NVDA": ["nvidia", "nvda", "gpu", "cuda", "jensen huang"],
    "SPY": ["s&p 500", "spy", "s&p500"],
    "QQQ": ["nasdaq", "qqq", "tech stocks"],
    "GLD": ["gold", "gld", "precious metals", "xau"],
}


def _parse_published(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        import time
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


def _detect_symbols(text: str) -> list[str]:
    text_lower = text.lower()
    return [
        ticker
        for ticker, keywords in SYMBOL_KEYWORDS.items()
        if any(kw in text_lower for kw in keywords)
    ]


def fetch_news(feeds: Optional[list[str]] = None) -> int:
    """Fetch news from RSS feeds and persist. Returns total articles saved."""
    if feeds is None:
        feeds = RSS_FEEDS

    total = 0
    session = get_session()
    try:
        for feed_url in feeds:
            try:
                parsed = feedparser.parse(feed_url)
                log.info("news.feed_parsed", url=feed_url, entries=len(parsed.entries))
            except Exception as exc:
                log.error("news.feed_error", url=feed_url, error=str(exc))
                continue

            for entry in parsed.entries:
                headline = getattr(entry, "title", "").strip()
                if not headline:
                    continue

                summary = getattr(entry, "summary", None)
                url = getattr(entry, "link", None)
                source = parsed.feed.get("title", feed_url)
                published_at = _parse_published(entry)

                import json
                raw = json.dumps({
                    "id": getattr(entry, "id", None),
                    "tags": [t.get("term") for t in getattr(entry, "tags", [])],
                })

                try:
                    result = session.execute(
                        text(_INSERT_NEWS),
                        {
                            "headline": headline,
                            "summary": summary,
                            "source": source,
                            "url": url,
                            "published_at": published_at,
                            "raw_json": raw,
                        },
                    ).fetchone()

                    if result:
                        news_id = result[0]
                        symbols = _detect_symbols(f"{headline} {summary or ''}")
                        for ticker in symbols:
                            session.execute(
                                text(_LINK_SYMBOL),
                                {"news_id": news_id, "ticker": ticker},
                            )
                        total += 1

                except Exception as exc:
                    log.error("news.insert_error", headline=headline[:60], error=str(exc))
                    continue

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    log.info("news.fetch_complete", total_saved=total)
    return total
