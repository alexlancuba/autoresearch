"""
Evaluation metrics for the Trade Show Trend Analysis system.

This is the fixed evaluation infrastructure (part of prepare.py equivalent).
The agent CANNOT modify this file — it defines the ground truth metrics.
"""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"


def evaluate_prediction_accuracy(
    predictions: list[dict],
    actuals: list[dict],
) -> float:
    """Core eval metric: how accurately did the agent predict trend outcomes.

    Args:
        predictions: list of {trend_name, predicted_score, predicted_lifecycle}
        actuals: list of {trend_name, actual_score, actual_lifecycle}

    Returns:
        Accuracy score from 0.0 to 1.0
    """
    if not predictions or not actuals:
        return 0.0

    pred_map = {p["trend_name"]: p for p in predictions}
    actual_map = {a["trend_name"]: a for a in actuals}

    common = set(pred_map.keys()) & set(actual_map.keys())
    if not common:
        return 0.0

    # Score component 1: Ranking accuracy (Spearman-like)
    pred_ranked = sorted(common, key=lambda t: pred_map[t].get("predicted_score", 0), reverse=True)
    actual_ranked = sorted(common, key=lambda t: actual_map[t].get("actual_score", 0), reverse=True)

    rank_errors = 0
    for i, trend in enumerate(pred_ranked):
        actual_rank = actual_ranked.index(trend)
        rank_errors += abs(i - actual_rank)
    max_rank_error = len(common) * (len(common) - 1) / 2
    ranking_accuracy = 1.0 - (rank_errors / max(max_rank_error, 1))

    # Score component 2: Score accuracy (normalized MAE)
    score_errors = sum(
        abs(pred_map[t].get("predicted_score", 0) - actual_map[t].get("actual_score", 0)) / 100.0
        for t in common
    )
    score_accuracy = 1.0 - (score_errors / len(common))

    # Score component 3: Lifecycle accuracy
    lifecycle_matches = sum(
        1 for t in common
        if pred_map[t].get("predicted_lifecycle") == actual_map[t].get("actual_lifecycle")
    )
    lifecycle_accuracy = lifecycle_matches / len(common)

    # Weighted combination
    final = (
        0.40 * ranking_accuracy
        + 0.35 * score_accuracy
        + 0.25 * lifecycle_accuracy
    )
    return round(max(min(final, 1.0), 0.0), 4)


def evaluate_signal_yield(
    extracted_signals: list[dict],
    validated_signals: list[dict],
) -> float:
    """Eval metric for SignalCollector: what % of extracted signals were validated."""
    if not extracted_signals:
        return 0.0
    validated_ids = {s.get("id") for s in validated_signals}
    valid_count = sum(1 for s in extracted_signals if s.get("id") in validated_ids)
    return round(valid_count / len(extracted_signals), 4)


def evaluate_report_quality(report: str) -> dict:
    """Basic report quality metrics (placeholder for human eval integration)."""
    return {
        "word_count": len(report.split()),
        "paragraph_count": report.count("\n\n") + 1,
        "has_data_points": any(c.isdigit() for c in report),
        "has_recommendations": "recommend" in report.lower() or "should" in report.lower(),
    }


def load_ground_truth(show_name: str) -> Optional[list[dict]]:
    """Load ground truth outcomes for a completed trade show."""
    gt_path = DATA_DIR / "ground_truth" / f"{show_name.lower().replace(' ', '_')}.json"
    if gt_path.exists():
        with open(gt_path) as f:
            return json.load(f)
    return None
