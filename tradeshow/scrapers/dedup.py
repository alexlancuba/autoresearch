"""
Signal deduplication.

Prevents the same trend signal from being counted multiple times
when the same story appears across multiple sources.
"""

from __future__ import annotations

import hashlib
import re


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def _signal_hash(signal: dict) -> str:
    """Compute a dedup hash for a signal based on content and source."""
    parts = [
        _normalize_text(signal.get("text", "")),
        signal.get("source_url", ""),
        signal.get("trend_category", ""),
        "|".join(sorted(signal.get("trade_shows", []))),
    ]
    content = "|".join(parts)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def deduplicate_signals(
    new_signals: list[dict],
    existing_signals: Optional[list[dict]] = None,
) -> list[dict]:
    """Remove duplicate signals.

    Deduplicates within new_signals and against existing_signals.

    Args:
        new_signals: Newly extracted signals to deduplicate.
        existing_signals: Existing signals to check against.

    Returns:
        Deduplicated list of new signals.
    """
    if existing_signals is None:
        existing_signals = []

    # Build set of existing hashes
    existing_hashes: set[str] = set()
    for sig in existing_signals:
        existing_hashes.add(_signal_hash(sig))

    # Also track existing source URLs
    existing_urls: set[str] = set()
    for sig in existing_signals:
        url = sig.get("source_url", "")
        if url:
            existing_urls.add(url)

    # Deduplicate new signals
    seen_hashes: set[str] = set()
    unique: list[dict] = []

    for signal in new_signals:
        h = _signal_hash(signal)

        # Skip if we've seen this content before
        if h in existing_hashes or h in seen_hashes:
            continue

        # Skip if same URL + same trend category already exists
        url = signal.get("source_url", "")
        cat = signal.get("trend_category", "")
        url_cat_key = f"{url}|{cat}"
        if url and any(
            s.get("source_url") == url and s.get("trend_category") == cat
            for s in existing_signals
        ):
            continue

        seen_hashes.add(h)
        unique.append(signal)

    return unique


# Fix missing import
from typing import Optional
