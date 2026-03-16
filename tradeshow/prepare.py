"""
Trade Show Trend Analysis — Fixed Data Infrastructure.

This is the equivalent of autoresearch's prepare.py. It contains the fixed
infrastructure for data loading, source indexing, and evaluation. The agent
CANNOT modify this file — it defines the ground truth data pipeline.

Parallels to autoresearch:
- Data loading functions ↔ HuggingFace dataset download
- Trade show database ↔ tokenizer training data
- Signal extraction pipeline ↔ dataloader with best-fit packing
- evaluate_prediction_accuracy() ↔ evaluate_bpb()
"""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"

# ── Industry & Region Taxonomies (fixed) ─────────────────────────────────────

INDUSTRIES = [
    "Technology & Electronics",
    "Healthcare & Medical Devices",
    "Automotive & Transportation",
    "Food & Beverage",
    "Energy & Sustainability",
    "Fashion & Textiles",
    "Construction & Real Estate",
    "Agriculture & Farming",
    "Defense & Aerospace",
    "Retail & E-Commerce",
    "Manufacturing & Industrial",
    "Telecommunications",
    "Entertainment & Media",
    "Logistics & Supply Chain",
    "Finance & Fintech",
]

REGIONS = [
    "North America",
    "Europe",
    "Asia-Pacific",
    "Middle East & Africa",
    "Latin America",
]


# ── Data Loading ─────────────────────────────────────────────────────────────


def _load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def load_shows(industry: Optional[str] = None, region: Optional[str] = None) -> list[dict]:
    """Load trade show database, optionally filtered."""
    shows = _load_json("shows.json")
    if industry:
        shows = [s for s in shows if industry in s.get("industries", [])]
    if region:
        shows = [s for s in shows if s.get("region") == region]
    return shows


def load_signals(cycle_id: Optional[str] = None, industry: Optional[str] = None,
                 region: Optional[str] = None) -> list[dict]:
    """Load extracted signals, optionally filtered."""
    signals = _load_json("signals.json")
    if cycle_id:
        signals = [s for s in signals if s.get("cycle_id") == cycle_id]
    if industry:
        signals = [s for s in signals if industry in s.get("industries", [])]
    if region:
        signals = [s for s in signals if region in s.get("regions", [])]
    return signals


def load_trends(cycle_id: Optional[str] = None, industry: Optional[str] = None,
                region: Optional[str] = None) -> list[dict]:
    """Load computed trends, optionally filtered."""
    trends = _load_json("trends.json")
    if cycle_id:
        trends = [t for t in trends if t.get("cycle_id") == cycle_id]
    if industry:
        trends = [t for t in trends if industry in t.get("industries", [])]
    if region:
        trends = [t for t in trends if region in t.get("regions", [])]
    return trends


def load_cycles() -> list[dict]:
    """Load analysis cycle history (run history)."""
    return _load_json("cycles.json")


def get_industries() -> list[str]:
    """Return the fixed industry taxonomy."""
    return INDUSTRIES.copy()


def get_regions() -> list[str]:
    """Return the fixed region taxonomy."""
    return REGIONS.copy()


# ── Evaluation (fixed — the val_bpb equivalent) ─────────────────────────────


def evaluate_prediction_accuracy(
    predictions: list[dict],
    actuals: list[dict],
) -> float:
    """Core eval metric: how accurately did the agent predict trend outcomes.

    This is the val_bpb equivalent. The agent optimizes its models in train.py
    to maximize this metric.

    Args:
        predictions: list of {"trend_name": str, "predicted_score": float, "predicted_lifecycle": str}
        actuals: list of {"trend_name": str, "actual_score": float, "actual_lifecycle": str}

    Returns:
        Accuracy score from 0.0 to 1.0 (higher is better)
    """
    if not predictions or not actuals:
        return 0.0

    pred_map = {p["trend_name"]: p for p in predictions}
    actual_map = {a["trend_name"]: a for a in actuals}
    common = set(pred_map.keys()) & set(actual_map.keys())

    if not common:
        return 0.0

    # Component 1: Ranking accuracy (40% weight)
    pred_ranked = sorted(common, key=lambda t: pred_map[t].get("predicted_score", 0), reverse=True)
    actual_ranked = sorted(common, key=lambda t: actual_map[t].get("actual_score", 0), reverse=True)
    rank_errors = sum(abs(i - actual_ranked.index(t)) for i, t in enumerate(pred_ranked))
    max_rank_error = len(common) * (len(common) - 1) / 2
    ranking_accuracy = 1.0 - (rank_errors / max(max_rank_error, 1))

    # Component 2: Score accuracy (35% weight)
    score_errors = sum(
        abs(pred_map[t].get("predicted_score", 0) - actual_map[t].get("actual_score", 0)) / 100.0
        for t in common
    )
    score_accuracy = 1.0 - (score_errors / len(common))

    # Component 3: Lifecycle accuracy (25% weight)
    lifecycle_matches = sum(
        1 for t in common
        if pred_map[t].get("predicted_lifecycle") == actual_map[t].get("actual_lifecycle")
    )
    lifecycle_accuracy = lifecycle_matches / len(common)

    return round(
        max(min(0.40 * ranking_accuracy + 0.35 * score_accuracy + 0.25 * lifecycle_accuracy, 1.0), 0.0),
        4,
    )


def get_stats() -> dict:
    """Aggregate stats for the dashboard."""
    signals = load_signals()
    cycles = load_cycles()
    return {
        "total_signals": len(signals),
        "total_cycles": len(cycles),
        "total_industries": len(INDUSTRIES),
        "total_regions": len(REGIONS),
    }
