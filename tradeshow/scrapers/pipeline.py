"""
End-to-end scraping pipeline orchestration.

Runs scrapers -> LLM extraction -> dedup -> save signals + media -> log cycle.
Can be called programmatically from the API or CLI.
"""

from __future__ import annotations

import json
import logging
import pathlib
from datetime import datetime
from typing import Optional

from .run import run_scrape

logger = logging.getLogger(__name__)

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


def _load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _save_json(filename: str, data: list[dict]) -> None:
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


async def run_pipeline(
    offline: bool = False,
    max_results: int = 50,
    scope: str = "Full Scan",
) -> dict:
    """Run the full data collection pipeline.

    1. Run all scrapers (RSS, YouTube, etc.)
    2. Extract signals (LLM or offline)
    3. Deduplicate against existing signals
    4. Save signals and media
    5. Log a new analysis cycle

    Returns:
        Pipeline result summary dict.
    """
    # Run the scrape
    summary = await run_scrape(offline=offline, max_results=max_results)

    # Log a new cycle
    cycles = _load_json("cycles.json")
    signals = _load_json("signals.json")
    media = _load_json("media.json")

    cycle = {
        "id": summary["cycle_id"],
        "timestamp": summary["timestamp"],
        "scan_type": "live_scrape",
        "scope": scope,
        "signal_count": summary["total_signals"],
        "trend_count": len(_load_json("trends.json")),
        "industries_covered": len({
            ind for s in signals for ind in s.get("industries", [])
        }),
        "regions_covered": len({
            reg for s in signals for reg in s.get("regions", [])
        }),
        "model_version": "v1.0-live",
        "predictions": [],
        "eval_score": None,
    }
    cycles.insert(0, cycle)
    _save_json("cycles.json", cycles)

    summary["cycle"] = cycle
    summary["media_total"] = len(media)
    return summary
