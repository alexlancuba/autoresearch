"""
CLI entry point for the scraping pipeline.

Usage:
    python -m tradeshow.scrapers.run [--offline] [--max-results 50]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import sys
from datetime import datetime

# Ensure project root is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from tradeshow.scrapers.base import RawArticle
from tradeshow.scrapers.rss_scraper import RssScraper
from tradeshow.scrapers.web_scraper import WebScraper
from tradeshow.scrapers.youtube_scraper import YouTubeScraper
from tradeshow.scrapers.extractor import SignalExtractor
from tradeshow.scrapers.dedup import deduplicate_signals

logger = logging.getLogger(__name__)

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config.yaml"


def _load_config() -> dict:
    """Load scraping config from YAML, falling back to defaults."""
    try:
        import yaml
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except (ImportError, FileNotFoundError):
        return {}


def _load_show_names() -> list[str]:
    """Load trade show short names from the shows database."""
    path = DATA_DIR / "shows.json"
    if not path.exists():
        return []
    with open(path) as f:
        shows = json.load(f)
    return [s.get("short_name", "") for s in shows if s.get("short_name")]


def _load_existing_signals() -> list[dict]:
    """Load existing signals for deduplication."""
    path = DATA_DIR / "signals.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _save_signals(signals: list[dict]) -> None:
    """Save signals to the data directory."""
    path = DATA_DIR / "signals.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(signals, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _save_media(media: list[dict]) -> None:
    """Save media assets to the data directory."""
    path = DATA_DIR / "media.json"
    existing = []
    if path.exists():
        with open(path) as f:
            existing = json.load(f)

    # Merge by ID
    existing_ids = {m["id"] for m in existing}
    for m in media:
        if m["id"] not in existing_ids:
            existing.append(m)
            existing_ids.add(m["id"])

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
        f.write("\n")


async def run_scrape(
    offline: bool = False,
    max_results: int = 50,
) -> dict:
    """Run a full scraping cycle.

    Args:
        offline: If True, skip LLM extraction and use keyword matching.
        max_results: Max articles per scraper.

    Returns:
        Summary dict with counts.
    """
    config = _load_config()
    scraping_cfg = config.get("scraping", {})
    show_names = _load_show_names()
    cycle_id = f"scrape-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    all_articles: list[RawArticle] = []
    all_media: list[dict] = []

    # Phase 1: RSS scraping
    logger.info("Starting RSS scraper...")
    rss_feeds = scraping_cfg.get("rss_feeds", [])
    search_queries = scraping_cfg.get("search_queries", [
        "trade show trends 2026",
        "trade show booth design trends",
        "exhibit design innovation",
    ])
    rss_scraper = RssScraper(show_names=show_names)
    try:
        rss_articles = await rss_scraper.fetch(
            queries=search_queries,
            rss_feeds=rss_feeds,
            max_results=max_results,
        )
        all_articles.extend(rss_articles)
        logger.info(f"RSS: fetched {len(rss_articles)} articles")
    except Exception as e:
        logger.warning(f"RSS scraping failed: {e}")

    # Phase 2: YouTube scraping (if API key available)
    import os
    yt_key = os.environ.get("YOUTUBE_API_KEY", "")
    if yt_key:
        logger.info("Starting YouTube scraper...")
        yt_scraper = YouTubeScraper(
            api_key=yt_key,
            show_names=show_names[:10],
            year=2026,
        )
        try:
            yt_articles = await yt_scraper.fetch(max_results=max_results)
            all_articles.extend(yt_articles)
            # Extract media assets from YouTube videos
            yt_media = YouTubeScraper.extract_media_assets(yt_articles, cycle_id)
            all_media.extend(yt_media)
            logger.info(f"YouTube: {len(yt_articles)} videos, {len(yt_media)} media assets")
        except Exception as e:
            logger.warning(f"YouTube scraping failed: {e}")
    else:
        logger.info("Skipping YouTube (no YOUTUBE_API_KEY)")

    # Phase 3: Signal extraction
    logger.info(f"Extracting signals from {len(all_articles)} articles...")
    extractor = SignalExtractor()
    if offline or not os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("Using offline keyword extraction")
        new_signals = extractor.extract_signals_offline(all_articles, cycle_id)
    else:
        new_signals = extractor.extract_signals(all_articles, cycle_id)

    # Phase 4: Deduplication
    existing_signals = _load_existing_signals()
    unique_signals = deduplicate_signals(new_signals, existing_signals)
    logger.info(f"Dedup: {len(new_signals)} -> {len(unique_signals)} new unique signals")

    # Phase 5: Save
    combined_signals = existing_signals + unique_signals
    _save_signals(combined_signals)

    if all_media:
        _save_media(all_media)

    summary = {
        "cycle_id": cycle_id,
        "articles_fetched": len(all_articles),
        "signals_extracted": len(new_signals),
        "signals_unique": len(unique_signals),
        "total_signals": len(combined_signals),
        "media_assets": len(all_media),
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info(f"Scrape complete: {summary}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Trade Show Trend Scraper")
    parser.add_argument("--offline", action="store_true", help="Use keyword extraction instead of LLM")
    parser.add_argument("--max-results", type=int, default=50, help="Max articles per scraper")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    summary = asyncio.run(run_scrape(
        offline=args.offline,
        max_results=args.max_results,
    ))

    print("\n--- Scrape Summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
