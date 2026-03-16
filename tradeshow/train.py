"""
Trade Show Trend Analysis Engine — the agent-modifiable file.

This is the equivalent of autoresearch's train.py. The agent modifies the
algorithms, weights, and models in this file to improve trend prediction
accuracy. The eval metric is retrospective prediction accuracy: how well
do the models predict what actually happened at subsequent trade shows.

The autoresearch loop:
1. Agent modifies a model parameter or algorithm in this file
2. Runs analysis on historical data (past shows)
3. Evaluates: how well do modified models predict what happened at the next show?
4. Keeps the modification if prediction accuracy improves, discards if not
5. Logs the experiment to results.tsv
6. Repeats
"""

import json
import math
from pathlib import Path
from collections import defaultdict, Counter

DATA_DIR = Path(__file__).parent / "data"

# ══════════════════════════════════════════════════════════════════════════════
# MODIFIABLE HYPERPARAMETERS — The agent tunes these
# ══════════════════════════════════════════════════════════════════════════════

# Signal clustering
CLUSTERING_THRESHOLD = 0.65  # similarity threshold for grouping signals
KEYWORD_OVERLAP_WEIGHT = 0.4
INDUSTRY_OVERLAP_WEIGHT = 0.3
TEMPORAL_PROXIMITY_WEIGHT = 0.3

# Trend momentum scoring weights
MOMENTUM_WEIGHTS = {
    "recency": 0.30,
    "frequency": 0.25,
    "geographic_spread": 0.20,
    "industry_breadth": 0.25,
}

# Confidence scoring weights
CONFIDENCE_WEIGHTS = {
    "signal_count": 0.35,
    "source_diversity": 0.30,
    "cross_validation": 0.35,
}

# Lifecycle classification thresholds (composite_score ranges)
LIFECYCLE_THRESHOLDS = {
    "emerging": (0, 25),
    "growing": (25, 50),
    "mature": (50, 75),
    "declining": (75, 100),  # inverted: high score but negative velocity
}

# Regional weights (relative importance of signals from each region)
REGIONAL_WEIGHTS = {
    "North America": 1.0,
    "Europe": 0.95,
    "Asia-Pacific": 0.90,
    "Middle East & Africa": 0.75,
    "Latin America": 0.70,
}

# Composite score formula coefficients
SCORE_COEFFICIENTS = {
    "mention_count": 2.5,
    "show_count": 5.0,
    "avg_signal_strength": 15.0,
    "industry_breadth": 3.0,
    "regional_spread": 4.0,
    "velocity_bonus": 2.0,
}

# Velocity calculation
VELOCITY_WINDOW_CYCLES = 3
VELOCITY_SMOOTHING = 0.1

# Cross-industry detection
CROSS_INDUSTRY_MIN_SECTORS = 3

# Prediction model weights
PREDICTION_WEIGHTS = {
    "current_momentum": 0.40,
    "historical_pattern": 0.30,
    "industry_adoption_curve": 0.20,
    "seasonal_factor": 0.10,
}

# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS — The agent modifies these algorithms
# ══════════════════════════════════════════════════════════════════════════════

def compute_signal_similarity(signal_a: dict, signal_b: dict) -> float:
    """Compute similarity between two signals for clustering."""
    # Keyword overlap
    kw_a = set(signal_a.get("text", "").lower().split())
    kw_b = set(signal_b.get("text", "").lower().split())
    keyword_sim = len(kw_a & kw_b) / max(len(kw_a | kw_b), 1)

    # Industry overlap
    ind_a = set(signal_a.get("industries", []))
    ind_b = set(signal_b.get("industries", []))
    industry_sim = len(ind_a & ind_b) / max(len(ind_a | ind_b), 1)

    # Same trend category
    category_match = 1.0 if signal_a.get("trend_category") == signal_b.get("trend_category") else 0.0

    return (
        KEYWORD_OVERLAP_WEIGHT * keyword_sim
        + INDUSTRY_OVERLAP_WEIGHT * industry_sim
        + TEMPORAL_PROXIMITY_WEIGHT * category_match
    )


def cluster_signals(signals: list[dict]) -> dict[str, list[dict]]:
    """Group signals into trend clusters based on similarity."""
    clusters: dict[str, list[dict]] = defaultdict(list)
    for signal in signals:
        category = signal.get("trend_category", "uncategorized")
        clusters[category].append(signal)
    return dict(clusters)


def compute_composite_score(
    mention_count: int,
    show_count: int,
    avg_strength: float,
    industry_count: int,
    region_count: int,
    velocity: float = 0.0,
) -> float:
    """Compute the composite trend score (the 52.8, 46.3, etc. in the dashboard)."""
    score = (
        SCORE_COEFFICIENTS["mention_count"] * mention_count
        + SCORE_COEFFICIENTS["show_count"] * show_count
        + SCORE_COEFFICIENTS["avg_signal_strength"] * avg_strength
        + SCORE_COEFFICIENTS["industry_breadth"] * industry_count
        + SCORE_COEFFICIENTS["regional_spread"] * region_count
        + SCORE_COEFFICIENTS["velocity_bonus"] * max(velocity, 0)
    )
    return round(min(score, 100.0), 1)


def compute_confidence(
    signal_count: int,
    source_types: set[str],
    cross_validated: bool,
) -> float:
    """Compute confidence score for a trend (the 82%, 75%, etc.)."""
    # Signal count contribution (diminishing returns)
    count_score = min(signal_count / 15.0, 1.0)

    # Source diversity contribution
    diversity_score = min(len(source_types) / 5.0, 1.0)

    # Cross-validation bonus
    cv_score = 1.0 if cross_validated else 0.5

    confidence = (
        CONFIDENCE_WEIGHTS["signal_count"] * count_score
        + CONFIDENCE_WEIGHTS["source_diversity"] * diversity_score
        + CONFIDENCE_WEIGHTS["cross_validation"] * cv_score
    )
    return round(min(confidence, 1.0), 2)


def classify_lifecycle(composite_score: float, velocity: float = 0.0) -> str:
    """Classify trend lifecycle stage based on score and velocity."""
    if velocity < -0.1 and composite_score > 30:
        return "declining"
    if composite_score < LIFECYCLE_THRESHOLDS["emerging"][1]:
        return "emerging"
    if composite_score < LIFECYCLE_THRESHOLDS["growing"][1]:
        return "growing"
    return "mature"


def detect_cross_industry(industries: list[str]) -> bool:
    """Determine if a trend spans enough industries to be cross-industry."""
    return len(set(industries)) >= CROSS_INDUSTRY_MIN_SECTORS


def compute_velocity(current_score: float, previous_scores: list[float]) -> float:
    """Compute trend velocity (rate of change over recent cycles)."""
    if not previous_scores:
        return 0.0
    recent = previous_scores[-VELOCITY_WINDOW_CYCLES:]
    avg_previous = sum(recent) / len(recent)
    return round((current_score - avg_previous) / max(avg_previous, 1.0), 3)


def predict_next_show(trend: dict, show: dict) -> dict:
    """Predict trend prominence at an upcoming show."""
    base_score = trend.get("composite_score", 0)
    velocity = trend.get("velocity", 0)
    trend_industries = set(trend.get("industries", []))
    show_industries = set(show.get("industries", []))
    industry_relevance = len(trend_industries & show_industries) / max(len(show_industries), 1)

    predicted_score = (
        PREDICTION_WEIGHTS["current_momentum"] * base_score
        + PREDICTION_WEIGHTS["historical_pattern"] * base_score * 0.9
        + PREDICTION_WEIGHTS["industry_adoption_curve"] * base_score * industry_relevance
        + PREDICTION_WEIGHTS["seasonal_factor"] * base_score * (1 + velocity)
    )

    return {
        "trend_name": trend.get("name", ""),
        "show_name": show.get("name", ""),
        "predicted_score": round(min(predicted_score, 100), 1),
        "predicted_lifecycle": trend.get("lifecycle", "emerging"),
        "industry_relevance": round(industry_relevance, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS PIPELINE — Orchestrates the full analysis cycle
# ══════════════════════════════════════════════════════════════════════════════

def run_analysis(
    signals: list[dict],
    industry_filter: str | None = None,
    region_filter: str | None = None,
) -> list[dict]:
    """Run the full trend analysis pipeline on a set of signals.

    This is the main entry point. The agent improves this pipeline by
    modifying the hyperparameters and algorithms above.
    """
    # Filter signals
    filtered = signals
    if industry_filter:
        filtered = [s for s in filtered if industry_filter in s.get("industries", [])]
    if region_filter:
        filtered = [s for s in filtered if region_filter in s.get("regions", [])]

    # Cluster signals into trend groups
    clusters = cluster_signals(filtered)

    # Score and rank trends
    trends = []
    for trend_name, cluster_signals_list in clusters.items():
        all_industries = []
        all_regions = []
        all_shows = set()
        all_source_types = set()
        total_strength = 0.0

        for sig in cluster_signals_list:
            all_industries.extend(sig.get("industries", []))
            all_regions.extend(sig.get("regions", []))
            all_shows.update(sig.get("trade_shows", []))
            all_source_types.add(sig.get("source_type", ""))
            total_strength += sig.get("strength", 0)

        mention_count = len(cluster_signals_list)
        show_count = len(all_shows)
        avg_strength = total_strength / max(mention_count, 1)
        unique_industries = list(set(all_industries))
        unique_regions = list(set(all_regions))

        score = compute_composite_score(
            mention_count=mention_count,
            show_count=show_count,
            avg_strength=avg_strength,
            industry_count=len(unique_industries),
            region_count=len(unique_regions),
        )

        confidence = compute_confidence(
            signal_count=mention_count,
            source_types=all_source_types,
            cross_validated=show_count >= 2,
        )

        lifecycle = classify_lifecycle(score)
        cross_industry = detect_cross_industry(all_industries)

        trends.append({
            "name": trend_name,
            "composite_score": score,
            "confidence": confidence,
            "lifecycle": lifecycle,
            "cross_industry": cross_industry,
            "industries": unique_industries,
            "regions": unique_regions,
            "signal_count": mention_count,
            "mention_count": mention_count,
            "show_count": show_count,
            "signal_ids": [s.get("id", "") for s in cluster_signals_list],
        })

    # Sort by composite score descending and assign ranks
    trends.sort(key=lambda t: t["composite_score"], reverse=True)
    for i, trend in enumerate(trends):
        trend["rank"] = i + 1

    return trends


def run_evaluation(predictions: list[dict], actuals: list[dict]) -> float:
    """Evaluate prediction accuracy — the val_bpb equivalent.

    Compares predicted trend scores/rankings against actual outcomes
    after a trade show concludes. Returns a score from 0 to 1 where
    higher is better.
    """
    if not predictions or not actuals:
        return 0.0

    pred_map = {p["trend_name"]: p["predicted_score"] for p in predictions}
    actual_map = {a["trend_name"]: a.get("actual_score", 0) for a in actuals}

    common_trends = set(pred_map.keys()) & set(actual_map.keys())
    if not common_trends:
        return 0.0

    # Mean absolute error normalized to 0-1 scale
    total_error = sum(
        abs(pred_map[t] - actual_map[t]) / 100.0 for t in common_trends
    )
    mae = total_error / len(common_trends)

    # Convert error to accuracy (1 - MAE)
    return round(max(1.0 - mae, 0.0), 4)
