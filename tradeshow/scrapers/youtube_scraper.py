"""
YouTube scraper for booth tour videos and trade show content.

Uses the YouTube Data API v3 (free tier: 10,000 units/day).
Extracts video metadata, high-res thumbnails, and embed URLs.

Thumbnails serve double duty: they are free visual media assets
that represent booth designs and trade show content.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseScraper, RawArticle

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Default search queries for trade show booth content
DEFAULT_VIDEO_QUERIES = [
    '"{show}" booth tour {year}',
    '"{show}" walkthrough {year}',
    '"{show}" exhibit highlights {year}',
    '"{show}" best booths {year}',
]


class YouTubeScraper(BaseScraper):
    """Scrapes YouTube for booth tour videos and trade show content."""

    name = "youtube"
    source_type = "booth_photography"  # Videos are visual content
    rate_limit = 1.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        show_names: Optional[list[str]] = None,
        year: int = 2026,
    ):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        self.show_names = show_names or []
        self.year = year

    async def fetch(
        self,
        queries: Optional[list[str]] = None,
        max_results: int = 50,
    ) -> list[RawArticle]:
        """Fetch video metadata from YouTube search.

        Args:
            queries: Search queries. If None, generates from show_names.
            max_results: Max videos to return total.

        Returns:
            List of RawArticle objects with video metadata and thumbnail URLs.
        """
        if not self.api_key:
            logger.warning("No YouTube API key configured. Set YOUTUBE_API_KEY env var.")
            return []

        search_queries = queries or self._generate_queries()
        articles: list[RawArticle] = []
        per_query_limit = max(5, max_results // max(len(search_queries), 1))

        async with httpx.AsyncClient(timeout=30) as client:
            for query in search_queries:
                try:
                    videos = await self._search_videos(client, query, per_query_limit)
                    articles.extend(videos)
                    logger.info(f"Found {len(videos)} videos for: {query}")
                    await asyncio.sleep(self.rate_limit)
                except Exception as e:
                    logger.warning(f"YouTube search failed for '{query}': {e}")

        # Deduplicate by video ID
        seen_ids: set[str] = set()
        unique: list[RawArticle] = []
        for article in articles:
            vid_id = article.metadata.get("video_id", "")
            if vid_id and vid_id not in seen_ids:
                seen_ids.add(vid_id)
                unique.append(article)

        logger.info(f"YouTube scraper: {len(unique)} unique videos")
        return unique[:max_results]

    def _generate_queries(self) -> list[str]:
        """Generate search queries from show names and templates."""
        queries = []
        for show in self.show_names[:15]:  # Cap to stay within quota
            for template in DEFAULT_VIDEO_QUERIES[:2]:  # Use first 2 templates
                queries.append(template.format(show=show, year=self.year))
        return queries

    async def _search_videos(
        self, client: httpx.AsyncClient, query: str, max_results: int
    ) -> list[RawArticle]:
        """Search YouTube and return video articles with thumbnails."""
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 25),
            "order": "relevance",
            "key": self.api_key,
        }

        response = await client.get(YOUTUBE_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

        articles = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")

            if not video_id:
                continue

            # Extract all available thumbnail sizes
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_urls = []
            for size in ["maxres", "high", "medium", "default"]:
                if size in thumbnails:
                    thumbnail_urls.append(thumbnails[size]["url"])

            # Best available thumbnail
            best_thumbnail = thumbnail_urls[0] if thumbnail_urls else ""

            # Also construct direct thumbnail URLs (sometimes higher res)
            direct_thumbs = [
                f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
                f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            ]

            published = snippet.get("publishedAt", "")
            channel = snippet.get("channelTitle", "")

            articles.append(RawArticle(
                url=f"https://www.youtube.com/watch?v={video_id}",
                title=snippet.get("title", ""),
                text=snippet.get("description", ""),
                source_name=f"YouTube ({channel})",
                source_type="booth_photography",
                published_at=published,
                images=direct_thumbs + thumbnail_urls,
                video_urls=[
                    f"https://www.youtube.com/embed/{video_id}",
                ],
                metadata={
                    "video_id": video_id,
                    "channel": channel,
                    "embed_url": f"https://www.youtube.com/embed/{video_id}",
                    "thumbnail_urls": thumbnail_urls,
                    "direct_thumbnails": direct_thumbs,
                },
            ))

        return articles

    @staticmethod
    def extract_media_assets(articles: list[RawArticle], cycle_id: str = "") -> list[dict]:
        """Convert YouTube video articles into MediaAsset dicts.

        This is called separately from signal extraction because videos
        produce both signals (trend data) and media assets (visuals).
        """
        media = []
        for article in articles:
            video_id = article.metadata.get("video_id", "")
            if not video_id:
                continue

            # Create a thumbnail media asset
            thumbnails = article.metadata.get("direct_thumbnails", [])
            best_thumb = thumbnails[0] if thumbnails else ""
            small_thumb = thumbnails[2] if len(thumbnails) > 2 else best_thumb

            media.append({
                "id": f"yt-thumb-{video_id}",
                "url": best_thumb,
                "thumbnail_url": small_thumb,
                "media_type": "thumbnail",
                "source": "youtube",
                "source_url": article.url,
                "caption": article.title,
                "trade_shows": article.trade_show_mentions,
                "industries": [],
                "trend_categories": [],
                "tags": ["booth tour", "video", "youtube"],
                "width": 1280,
                "height": 720,
                "fetched_at": datetime.utcnow().isoformat(),
                "cycle_id": cycle_id,
            })

            # Create a video media asset
            embed_url = article.metadata.get("embed_url", "")
            if embed_url:
                media.append({
                    "id": f"yt-video-{video_id}",
                    "url": embed_url,
                    "thumbnail_url": small_thumb,
                    "media_type": "video",
                    "source": "youtube",
                    "source_url": article.url,
                    "caption": article.title,
                    "trade_shows": article.trade_show_mentions,
                    "industries": [],
                    "trend_categories": [],
                    "tags": ["booth tour", "video", "youtube"],
                    "width": 1920,
                    "height": 1080,
                    "fetched_at": datetime.utcnow().isoformat(),
                    "cycle_id": cycle_id,
                })

        return media
