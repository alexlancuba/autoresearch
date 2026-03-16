"""
Scraping infrastructure for the Trade Show Trend Analysis system.

This package handles real data collection from public sources:
- RSS feeds (Google News, trade publications)
- Web articles (TSNN, EventMarketer, exhibitor sites)
- YouTube (booth tour videos, thumbnails)
- Social media (Twitter/X hashtags, Instagram)
"""

from .base import BaseScraper, RawArticle
from .rss_scraper import RssScraper
from .web_scraper import WebScraper
from .extractor import SignalExtractor
from .dedup import deduplicate_signals

__all__ = [
    "BaseScraper",
    "RawArticle",
    "RssScraper",
    "WebScraper",
    "SignalExtractor",
    "deduplicate_signals",
]
