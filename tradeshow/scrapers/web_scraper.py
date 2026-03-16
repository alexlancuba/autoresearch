"""
Generic web article scraper.

Fetches and extracts main content from trade show news articles,
press releases, and exhibitor pages using httpx + beautifulsoup4.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """Scrapes web articles and extracts main text content + images."""

    name = "web"
    source_type = "media_coverage"
    rate_limit = 2.0

    def __init__(self, show_names: Optional[list[str]] = None):
        self.show_names = show_names or []

    async def fetch(
        self,
        queries: list[str],
        max_results: int = 20,
    ) -> list[RawArticle]:
        """Fetch and parse web pages from the given URLs.

        Args:
            queries: List of URLs to fetch (not search queries).
            max_results: Max articles to return.

        Returns:
            List of RawArticle objects with extracted content.
        """
        articles: list[RawArticle] = []

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "TradeShowTrendAgent/1.0"},
        ) as client:
            for url in queries[:max_results]:
                try:
                    article = await self._fetch_page(client, url)
                    if article:
                        articles.append(article)
                    await asyncio.sleep(self.rate_limit)
                except Exception as e:
                    logger.warning(f"Failed to fetch {url}: {e}")

        # Detect trade show mentions
        for article in articles:
            if self.show_names:
                combined = f"{article.title} {article.text}"
                article.trade_show_mentions = self._detect_trade_shows(
                    combined, self.show_names
                )

        return articles

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> Optional[RawArticle]:
        """Fetch a single page and extract content."""
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]

        # Extract main content
        text = self._extract_main_text(soup)

        # Extract images
        images = self._extract_images(soup, url)

        # Determine source name from domain
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")

        return RawArticle(
            url=url,
            title=title,
            text=text,
            source_name=domain,
            source_type=self.source_type,
            images=images,
        )

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """Extract the main article text from an HTML page."""
        # Remove script, style, nav, footer elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try <article> tag first
        article = soup.find("article")
        if article:
            return self._clean_text(article.get_text(separator=" "))

        # Try common content selectors
        for selector in [
            "div.article-content",
            "div.post-content",
            "div.entry-content",
            "main",
            "div.content",
        ]:
            content = soup.select_one(selector)
            if content:
                return self._clean_text(content.get_text(separator=" "))

        # Fallback: largest text block in <p> tags
        paragraphs = soup.find_all("p")
        if paragraphs:
            text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
            return self._clean_text(text)

        return ""

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract image URLs from the page."""
        from urllib.parse import urljoin
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src or src.startswith("data:"):
                continue
            full_url = urljoin(base_url, src)
            # Filter out tiny icons and tracking pixels
            width = img.get("width", "")
            height = img.get("height", "")
            if width and width.isdigit() and int(width) < 50:
                continue
            if height and height.isdigit() and int(height) < 50:
                continue
            images.append(full_url)
        return images[:20]  # Cap at 20 images per page

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted text."""
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]  # Cap at 5000 chars
