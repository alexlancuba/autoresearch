"""
RSS feed scraper for trade show news.

Sources:
- Google News RSS (free, no API key, structured output)
- Trade publication RSS feeds (TSNN, EventMarketer, Exhibitor Magazine)
- Industry-specific publication feeds

This is the highest-value, lowest-effort scraper because RSS feeds are
free, structured, and cover the most important trade show news sources.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore[assignment]

import httpx

from .base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)

# Google News RSS base URL
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Default trade show publication feeds
DEFAULT_FEEDS = [
    {
        "url": "https://www.tsnn.com/rss",
        "name": "TSNN",
        "source_type": "media_coverage",
    },
    {
        "url": "https://www.eventmarketer.com/feed/",
        "name": "EventMarketer",
        "source_type": "media_coverage",
    },
    {
        "url": "https://www.exhibitoronline.com/rss/rss.asp",
        "name": "Exhibitor Magazine",
        "source_type": "industry_publication",
    },
]

# Default search queries for Google News RSS
DEFAULT_QUERIES = [
    "trade show trends 2026",
    "trade show booth design trends",
    "exhibit design innovation",
    "CES 2026 exhibitors",
    "Hannover Messe 2026",
    "MEDICA trade show",
    "trade show technology",
    "exhibitor booth experience",
    "trade show sustainability",
    "trade show AI automation",
]


class RssScraper(BaseScraper):
    """Scrapes RSS feeds from trade show news sources and Google News."""

    name = "rss"
    source_type = "media_coverage"
    rate_limit = 1.0  # 1 second between RSS fetches

    def __init__(
        self,
        feeds: Optional[list[dict]] = None,
        queries: Optional[list[str]] = None,
        show_names: Optional[list[str]] = None,
    ):
        self.feeds = feeds or DEFAULT_FEEDS
        self.search_queries = queries or DEFAULT_QUERIES
        self.show_names = show_names or []

    async def fetch(
        self,
        queries: Optional[list[str]] = None,
        max_results: int = 50,
        rss_feeds: Optional[list[dict]] = None,
    ) -> list[RawArticle]:
        """Fetch articles from RSS feeds and Google News searches.

        Args:
            queries: Override search queries. If None, uses configured queries.
            max_results: Max total articles to return.
            rss_feeds: Override feed list from config.

        Returns:
            List of RawArticle objects.
        """
        if feedparser is None:
            logger.warning("feedparser not installed. Install with: pip install feedparser")
            return []

        if rss_feeds:
            self.feeds = rss_feeds
        search_queries = queries or self.search_queries
        articles: list[RawArticle] = []

        # Fetch from configured publication feeds
        for feed_config in self.feeds:
            try:
                feed_articles = await self._fetch_feed(
                    feed_config["url"],
                    feed_config["name"],
                    feed_config.get("source_type", "media_coverage"),
                )
                articles.extend(feed_articles)
                logger.info(f"Fetched {len(feed_articles)} articles from {feed_config['name']}")
                await asyncio.sleep(self.rate_limit)
            except Exception as e:
                logger.warning(f"Failed to fetch feed {feed_config['name']}: {e}")

        # Fetch from Google News RSS for each query
        for query in search_queries:
            try:
                google_articles = await self._fetch_google_news(query)
                articles.extend(google_articles)
                logger.info(f"Fetched {len(google_articles)} articles for query: {query}")
                await asyncio.sleep(self.rate_limit)
            except Exception as e:
                logger.warning(f"Failed Google News search for '{query}': {e}")

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[RawArticle] = []
        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique.append(article)

        # Detect trade show mentions
        for article in unique:
            if self.show_names:
                combined_text = f"{article.title} {article.text}"
                article.trade_show_mentions = self._detect_trade_shows(
                    combined_text, self.show_names
                )

        logger.info(f"RSS scraper: {len(unique)} unique articles (from {len(articles)} total)")
        return unique[:max_results]

    async def _fetch_feed(
        self, url: str, source_name: str, source_type: str
    ) -> list[RawArticle]:
        """Parse a single RSS feed URL."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TradeShowTrendAgent/1.0"})
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        articles = []

        for entry in feed.entries:
            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except (ValueError, TypeError):
                    pass

            # Extract text from summary/description
            text = ""
            if hasattr(entry, "summary"):
                text = entry.summary
            elif hasattr(entry, "description"):
                text = entry.description

            # Strip HTML tags for plain text
            text = self._strip_html(text)

            articles.append(RawArticle(
                url=getattr(entry, "link", ""),
                title=getattr(entry, "title", ""),
                text=text,
                source_name=source_name,
                source_type=source_type,
                published_at=published,
            ))

        return articles

    async def _fetch_google_news(self, query: str) -> list[RawArticle]:
        """Fetch articles from Google News RSS for a search query."""
        url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TradeShowTrendAgent/1.0"})
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        articles = []

        for entry in feed.entries:
            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except (ValueError, TypeError):
                    pass

            text = self._strip_html(getattr(entry, "summary", ""))

            articles.append(RawArticle(
                url=getattr(entry, "link", ""),
                title=getattr(entry, "title", ""),
                text=text,
                source_name=f"Google News ({query})",
                source_type="media_coverage",
                published_at=published,
            ))

        return articles

    @staticmethod
    def _strip_html(html: str) -> str:
        """Remove HTML tags from text."""
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean
