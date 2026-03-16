"""
Base scraper class and shared data models for the scraping pipeline.
"""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawArticle:
    """A raw piece of content fetched from any source."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    url: str = ""
    title: str = ""
    text: str = ""
    source_name: str = ""          # "TSNN", "Google News", "YouTube", etc.
    source_type: str = ""          # maps to SignalSourceType values
    published_at: str = ""         # ISO date
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    images: list[str] = field(default_factory=list)    # image URLs in article
    video_urls: list[str] = field(default_factory=list)
    trade_show_mentions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        """Hash for deduplication based on URL and title."""
        content = f"{self.url}|{self.title}".lower().strip()
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
            "images": self.images,
            "video_urls": self.video_urls,
            "trade_show_mentions": self.trade_show_mentions,
            "metadata": self.metadata,
        }


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    name: str = "base"
    source_type: str = "media_coverage"
    rate_limit: float = 2.0  # seconds between requests

    @abstractmethod
    async def fetch(
        self,
        queries: list[str],
        max_results: int = 20,
    ) -> list[RawArticle]:
        """Fetch raw articles from this source.

        Args:
            queries: Search queries or feed URLs to fetch.
            max_results: Maximum articles to return.

        Returns:
            List of RawArticle objects.
        """
        ...

    def _detect_trade_shows(self, text: str, show_names: list[str]) -> list[str]:
        """Detect trade show mentions in text."""
        text_lower = text.lower()
        found = []
        for name in show_names:
            if name.lower() in text_lower:
                found.append(name)
        return found
