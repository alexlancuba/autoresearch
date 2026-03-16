"""
Trade Show Trend Analysis — Fixed Data Infrastructure.

This is the equivalent of autoresearch's prepare.py. It contains the fixed
infrastructure for data loading, source indexing, and evaluation. The agent
CANNOT modify this file — it defines the ground truth data pipeline.

Parallels to autoresearch:
- Data loading functions    -> HuggingFace dataset download
- Trade show database       -> tokenizer training data
- Signal extraction pipeline -> dataloader with best-fit packing
- evaluate_prediction_accuracy() -> evaluate_bpb()
- Indexing functions         -> vocabulary / token_bytes lookup

Usage:
    from tradeshow.prepare import load_shows, load_signals, load_trends
    from tradeshow.prepare import evaluate_prediction_accuracy
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from tradeshow.models import Industry, Region, LifecycleStage

DATA_DIR = Path(__file__).parent / "data"

# ── Industry & Region Taxonomies (fixed — DO NOT MODIFY) ────────────────────

INDUSTRIES = [member.value for member in Industry]

REGIONS = [member.value for member in Region]

LIFECYCLE_STAGES = [member.value for member in LifecycleStage]


# ── Data Loading ─────────────────────────────────────────────────────────────


def _load_json(filename: str) -> list[dict]:
    """Load a JSON array from the data directory."""
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _save_json(filename: str, data: list[dict]) -> None:
    """Save a JSON array to the data directory."""
    path = DATA_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_shows(
    industry: Optional[str] = None,
    region: Optional[str] = None,
    tier: Optional[str] = None,
) -> list[dict]:
    """Load trade show database, optionally filtered.

    Args:
        industry: Filter by industry string (e.g., "Technology & Electronics")
        region: Filter by region string (e.g., "North America")
        tier: Filter by tier (e.g., "global_flagship", "regional_major", "niche")

    Returns:
        List of trade show dicts.
    """
    shows = _load_json("shows.json")
    if industry:
        shows = [s for s in shows if industry in s.get("industries", [])]
    if region:
        shows = [s for s in shows if s.get("region") == region]
    if tier:
        shows = [s for s in shows if s.get("tier") == tier]
    return shows


def load_signals(
    cycle_id: Optional[str] = None,
    industry: Optional[str] = None,
    region: Optional[str] = None,
    trend_category: Optional[str] = None,
) -> list[dict]:
    """Load extracted signals, optionally filtered.

    Args:
        cycle_id: Filter by analysis cycle (e.g., "cycle-001")
        industry: Filter by industry string
        region: Filter by region string
        trend_category: Filter by trend category name (e.g., "AI & Machine Learning")

    Returns:
        List of signal dicts.
    """
    signals = _load_json("signals.json")
    if cycle_id:
        signals = [s for s in signals if s.get("cycle_id") == cycle_id]
    if industry:
        signals = [s for s in signals if industry in s.get("industries", [])]
    if region:
        signals = [s for s in signals if region in s.get("regions", [])]
    if trend_category:
        signals = [s for s in signals if s.get("trend_category") == trend_category]
    return signals


def load_trends(
    cycle_id: Optional[str] = None,
    industry: Optional[str] = None,
    region: Optional[str] = None,
) -> list[dict]:
    """Load computed trends, optionally filtered.

    Args:
        cycle_id: Filter by analysis cycle
        industry: Filter by industry string
        region: Filter by region string

    Returns:
        List of trend dicts, sorted by rank.
    """
    trends = _load_json("trends.json")
    if cycle_id:
        trends = [t for t in trends if t.get("cycle_id") == cycle_id]
    if industry:
        trends = [t for t in trends if industry in t.get("industries", [])]
    if region:
        trends = [t for t in trends if region in t.get("regions", [])]
    return sorted(trends, key=lambda t: t.get("rank", 999))


def load_media(
    trade_show: Optional[str] = None,
    trend_category: Optional[str] = None,
    media_type: Optional[str] = None,
) -> list[dict]:
    """Load media assets, optionally filtered.

    Args:
        trade_show: Filter by trade show short name.
        trend_category: Filter by trend category.
        media_type: Filter by media type (photo, video, thumbnail, etc.).

    Returns:
        List of media asset dicts.
    """
    media = _load_json("media.json")
    if trade_show:
        media = [m for m in media if trade_show in m.get("trade_shows", [])]
    if trend_category:
        media = [m for m in media if trend_category in m.get("trend_categories", [])]
    if media_type:
        media = [m for m in media if m.get("media_type") == media_type]
    return media


def load_cycles() -> list[dict]:
    """Load analysis cycle history (run history).

    Returns:
        List of cycle dicts, sorted by timestamp descending (most recent first).
    """
    cycles = _load_json("cycles.json")
    return sorted(cycles, key=lambda c: c.get("timestamp", ""), reverse=True)


def get_industries() -> list[str]:
    """Return the fixed industry taxonomy."""
    return INDUSTRIES.copy()


def get_regions() -> list[str]:
    """Return the fixed region taxonomy."""
    return REGIONS.copy()


# ── Indexing Functions ───────────────────────────────────────────────────────


def build_show_index() -> dict[str, dict]:
    """Build a lookup index of shows by short_name.

    Returns:
        Dict mapping short_name -> show dict.
    """
    shows = load_shows()
    return {s["short_name"]: s for s in shows}


def build_signal_index(cycle_id: Optional[str] = None) -> dict[str, list[dict]]:
    """Build an index of signals grouped by trend_category.

    Args:
        cycle_id: Optional cycle filter.

    Returns:
        Dict mapping trend_category -> list of signal dicts.
    """
    signals = load_signals(cycle_id=cycle_id)
    index: dict[str, list[dict]] = defaultdict(list)
    for sig in signals:
        index[sig.get("trend_category", "unknown")].append(sig)
    return dict(index)


def build_show_signal_matrix(cycle_id: Optional[str] = None) -> dict[str, list[dict]]:
    """Build an index of signals grouped by trade show.

    Args:
        cycle_id: Optional cycle filter.

    Returns:
        Dict mapping show short_name -> list of signal dicts referencing that show.
    """
    signals = load_signals(cycle_id=cycle_id)
    matrix: dict[str, list[dict]] = defaultdict(list)
    for sig in signals:
        for show in sig.get("trade_shows", []):
            matrix[show].append(sig)
    return dict(matrix)


def get_trend_by_name(name: str, cycle_id: Optional[str] = None) -> Optional[dict]:
    """Look up a single trend by name.

    Args:
        name: Trend name (e.g., "AI & Machine Learning")
        cycle_id: Optional cycle filter.

    Returns:
        Trend dict or None if not found.
    """
    trends = load_trends(cycle_id=cycle_id)
    for t in trends:
        if t.get("name") == name:
            return t
    return None


def get_signals_for_trend(trend_name: str, cycle_id: Optional[str] = None) -> list[dict]:
    """Get all signals contributing to a named trend.

    Args:
        trend_name: The trend name to look up.
        cycle_id: Optional cycle filter.

    Returns:
        List of signal dicts for the trend.
    """
    return load_signals(cycle_id=cycle_id, trend_category=trend_name)


# ── Evaluation (fixed — the val_bpb equivalent — DO NOT MODIFY) ─────────────


def evaluate_prediction_accuracy(
    predictions: list[dict],
    actuals: list[dict],
) -> float:
    """Core eval metric: how accurately did the agent predict trend outcomes.

    This is the val_bpb equivalent. The agent optimizes its analysis models
    to maximize this metric. The function is FIXED and must not be modified.

    The metric combines three components:
    - Ranking accuracy (40%): Did the agent rank trends in the correct order?
    - Score accuracy (35%): How close were the predicted composite scores?
    - Lifecycle accuracy (25%): Did the agent predict the correct lifecycle stage?

    Args:
        predictions: list of dicts, each with:
            - "trend_name": str
            - "predicted_score": float (0-100 composite score)
            - "predicted_lifecycle": str ("emerging", "growing", "mature", "declining")
        actuals: list of dicts, each with:
            - "trend_name": str
            - "actual_score": float (0-100 composite score)
            - "actual_lifecycle": str ("emerging", "growing", "mature", "declining")

    Returns:
        Accuracy score from 0.0 to 1.0 (higher is better).
    """
    if not predictions or not actuals:
        return 0.0

    # Build lookup maps
    pred_map = {p["trend_name"]: p for p in predictions}
    actual_map = {a["trend_name"]: a for a in actuals}
    common = set(pred_map.keys()) & set(actual_map.keys())

    if not common:
        return 0.0

    # Component 1: Ranking accuracy (40% weight)
    # Measures how well the predicted ranking matches actual ranking
    pred_ranked = sorted(
        common,
        key=lambda t: pred_map[t].get("predicted_score", 0),
        reverse=True,
    )
    actual_ranked = sorted(
        common,
        key=lambda t: actual_map[t].get("actual_score", 0),
        reverse=True,
    )
    rank_errors = sum(
        abs(i - actual_ranked.index(t)) for i, t in enumerate(pred_ranked)
    )
    max_rank_error = len(common) * (len(common) - 1) / 2
    ranking_accuracy = 1.0 - (rank_errors / max(max_rank_error, 1))

    # Component 2: Score accuracy (35% weight)
    # Measures how close predicted scores are to actual scores
    score_errors = sum(
        abs(
            pred_map[t].get("predicted_score", 0)
            - actual_map[t].get("actual_score", 0)
        )
        / 100.0
        for t in common
    )
    score_accuracy = max(1.0 - (score_errors / len(common)), 0.0)

    # Component 3: Lifecycle accuracy (25% weight)
    # Measures how often the predicted lifecycle stage matches
    lifecycle_matches = sum(
        1
        for t in common
        if pred_map[t].get("predicted_lifecycle") == actual_map[t].get("actual_lifecycle")
    )
    lifecycle_accuracy = lifecycle_matches / len(common)

    # Weighted combination, clamped to [0, 1]
    combined = (
        0.40 * ranking_accuracy
        + 0.35 * score_accuracy
        + 0.25 * lifecycle_accuracy
    )
    return round(max(min(combined, 1.0), 0.0), 4)


# ── Statistics & Dashboard Helpers ───────────────────────────────────────────


def get_stats() -> dict:
    """Aggregate stats for the dashboard overview.

    Returns:
        Dict with summary statistics matching dashboard header cards.
    """
    shows = load_shows()
    signals = load_signals()
    trends = load_trends()
    cycles = load_cycles()

    # Count unique trade shows referenced in signals
    referenced_shows = set()
    for sig in signals:
        referenced_shows.update(sig.get("trade_shows", []))

    # Count unique industries and regions across signals
    signal_industries = set()
    signal_regions = set()
    for sig in signals:
        signal_industries.update(sig.get("industries", []))
        signal_regions.update(sig.get("regions", []))

    return {
        "total_shows": len(shows),
        "total_signals": len(signals),
        "total_trends": len(trends),
        "total_cycles": len(cycles),
        "total_industries": len(INDUSTRIES),
        "total_regions": len(REGIONS),
        "referenced_shows": len(referenced_shows),
        "signal_industries": len(signal_industries),
        "signal_regions": len(signal_regions),
    }


def get_latest_cycle() -> Optional[dict]:
    """Return the most recent analysis cycle, or None if no cycles exist."""
    cycles = load_cycles()
    return cycles[0] if cycles else None


# ── Validation ───────────────────────────────────────────────────────────────


def validate_data_integrity() -> list[str]:
    """Check data files for consistency issues.

    Returns:
        List of warning strings. Empty list means all data is consistent.
    """
    warnings: list[str] = []

    shows = load_shows()
    signals = load_signals()
    trends = load_trends()
    cycles = load_cycles()

    # Build show name set for validation
    show_names = {s["short_name"] for s in shows}

    # Check signals reference valid shows
    for sig in signals:
        for show in sig.get("trade_shows", []):
            if show not in show_names:
                warnings.append(
                    f"Signal {sig['id']} references unknown show: {show}"
                )

    # Check signals use valid industries
    for sig in signals:
        for ind in sig.get("industries", []):
            if ind not in INDUSTRIES:
                warnings.append(
                    f"Signal {sig['id']} uses unknown industry: {ind}"
                )

    # Check signals use valid regions
    for sig in signals:
        for reg in sig.get("regions", []):
            if reg not in REGIONS:
                warnings.append(
                    f"Signal {sig['id']} uses unknown region: {reg}"
                )

    # Check trends reference valid signal IDs
    signal_ids = {s["id"] for s in signals}
    for trend in trends:
        for sid in trend.get("signal_ids", []):
            if sid not in signal_ids:
                warnings.append(
                    f"Trend {trend['id']} ({trend['name']}) references unknown signal: {sid}"
                )

    # Check trends use valid lifecycle stages
    for trend in trends:
        if trend.get("lifecycle") not in LIFECYCLE_STAGES:
            warnings.append(
                f"Trend {trend['id']} uses unknown lifecycle: {trend.get('lifecycle')}"
            )

    # Check cycle IDs are consistent
    cycle_ids = {c["id"] for c in cycles}
    for sig in signals:
        if sig.get("cycle_id") and sig["cycle_id"] not in cycle_ids:
            warnings.append(
                f"Signal {sig['id']} references unknown cycle: {sig['cycle_id']}"
            )
    for trend in trends:
        if trend.get("cycle_id") and trend["cycle_id"] not in cycle_ids:
            warnings.append(
                f"Trend {trend['id']} references unknown cycle: {trend['cycle_id']}"
            )

    return warnings


# ── Main (self-test) ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Trade Show Trend Analysis — Data Infrastructure Check")
    print("=" * 60)
    print()

    # Load and display stats
    stats = get_stats()
    print(f"Trade shows in database:   {stats['total_shows']}")
    print(f"Signals extracted:         {stats['total_signals']}")
    print(f"Trends identified:         {stats['total_trends']}")
    print(f"Analysis cycles:           {stats['total_cycles']}")
    print(f"Industry categories:       {stats['total_industries']}")
    print(f"Region categories:         {stats['total_regions']}")
    print(f"Shows referenced:          {stats['referenced_shows']}")
    print()

    # Display latest cycle
    latest = get_latest_cycle()
    if latest:
        print(f"Latest cycle: {latest['scope']} ({latest['signal_count']} signals)")
        print(f"  Timestamp: {latest['timestamp']}")
        print(f"  Type: {latest['scan_type']}")
    print()

    # Display trend summary
    trends = load_trends()
    print("Top 10 Trends:")
    for t in trends[:10]:
        lifecycle_tag = t.get("lifecycle", "unknown")
        cross = " [cross-industry]" if t.get("cross_industry") else ""
        print(
            f"  #{t['rank']:2d}  {t['name']:<30s}  "
            f"score={t['composite_score']:5.1f}  "
            f"confidence={t['confidence']:.0%}  "
            f"{lifecycle_tag}{cross}"
        )
    print()

    # Validate data
    warnings = validate_data_integrity()
    if warnings:
        print(f"Data warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("Data integrity: OK (no warnings)")
    print()

    # Test evaluation function
    print("Evaluation function self-test:")
    test_predictions = [
        {"trend_name": "AI & Machine Learning", "predicted_score": 55.0, "predicted_lifecycle": "growing"},
        {"trend_name": "Sustainability & Green Tech", "predicted_score": 45.0, "predicted_lifecycle": "growing"},
        {"trend_name": "Robotics & Automation", "predicted_score": 40.0, "predicted_lifecycle": "growing"},
    ]
    test_actuals = [
        {"trend_name": "AI & Machine Learning", "actual_score": 52.8, "actual_lifecycle": "growing"},
        {"trend_name": "Sustainability & Green Tech", "actual_score": 46.3, "actual_lifecycle": "growing"},
        {"trend_name": "Robotics & Automation", "actual_score": 41.7, "actual_lifecycle": "growing"},
    ]
    score = evaluate_prediction_accuracy(test_predictions, test_actuals)
    print(f"  Test accuracy score: {score:.4f}")
    print()
    print("Done! Data infrastructure is ready.")
