"""
TrendAnalyzer — The Intelligence Engine (Agent 2).

Takes raw signals from SignalCollector and produces ranked trend analysis.
This is the core agent that maps to autoresearch's model training loop.

What it modifies (its train.py equivalent):
- Trend detection models (clustering, momentum, confidence scoring)
- Lifecycle classification
- Cross-industry correlation detection
- Prediction models

Eval metric: retrospective prediction accuracy — did the trends identified
actually manifest at subsequent trade shows?
"""

import json
import copy
import random
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"


class TrendAnalyzer:
    """Core analysis agent that synthesizes signals into ranked trends."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self._default_config()
        self._experiment_log: list[dict] = []

    @staticmethod
    def _default_config() -> dict:
        return {
            "clustering_threshold": 0.65,
            "momentum_weights": {
                "recency": 0.30,
                "frequency": 0.25,
                "geographic_spread": 0.20,
                "industry_breadth": 0.25,
            },
            "confidence_weights": {
                "signal_count": 0.35,
                "source_diversity": 0.30,
                "cross_validation": 0.35,
            },
            "lifecycle_thresholds": {
                "emerging": (0, 25),
                "growing": (25, 50),
                "mature": (50, 75),
            },
            "regional_weights": {
                "North America": 1.0,
                "Europe": 0.95,
                "Asia-Pacific": 0.90,
                "Middle East & Africa": 0.75,
                "Latin America": 0.70,
            },
            "velocity_window": 3,
        }

    def analyze(
        self,
        signals: list[dict],
        industry: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[dict]:
        """Run full trend analysis on signals. Returns ranked trends.

        For the initial version, loads pre-computed trends from seed data
        and applies filters. The actual clustering and scoring algorithms
        are implemented below for the autoresearch loop to iterate on.
        """
        # Load seed trends as baseline
        trends = self._load_seed_trends()

        # Apply filters
        if industry:
            trends = [t for t in trends if industry in t.get("industries", [])]
        if region:
            trends = [t for t in trends if region in t.get("regions", [])]

        # Re-rank after filtering
        trends.sort(key=lambda t: t.get("composite_score", 0), reverse=True)
        for i, t in enumerate(trends):
            t["rank"] = i + 1

        return trends

    def _cluster_signals(self, signals: list[dict]) -> dict[str, list[dict]]:
        """Group signals into trend clusters based on category and similarity."""
        clusters: dict[str, list[dict]] = {}
        for signal in signals:
            category = signal.get("trend_category", "uncategorized")
            clusters.setdefault(category, []).append(signal)
        return clusters

    def _score_trend(self, trend_name: str, signals: list[dict]) -> tuple[float, float]:
        """Compute composite score and confidence for a trend cluster."""
        if not signals:
            return 0.0, 0.0

        mention_count = len(signals)
        shows = set()
        source_types = set()
        industries = set()
        regions = set()
        total_strength = 0.0

        for s in signals:
            shows.update(s.get("trade_shows", []))
            source_types.add(s.get("source_type", ""))
            industries.update(s.get("industries", []))
            regions.update(s.get("regions", []))
            total_strength += s.get("strength", 0)

        avg_strength = total_strength / mention_count

        # Composite score using configurable weights
        mw = self.config["momentum_weights"]
        score = (
            mw["recency"] * mention_count * 2.5
            + mw["frequency"] * len(shows) * 5.0
            + mw["geographic_spread"] * len(regions) * 4.0
            + mw["industry_breadth"] * len(industries) * 3.0
        ) + avg_strength * 15.0
        score = min(round(score, 1), 100.0)

        # Confidence
        cw = self.config["confidence_weights"]
        count_score = min(mention_count / 15.0, 1.0)
        diversity_score = min(len(source_types) / 5.0, 1.0)
        cv_score = 1.0 if len(shows) >= 2 else 0.5
        confidence = round(
            cw["signal_count"] * count_score
            + cw["source_diversity"] * diversity_score
            + cw["cross_validation"] * cv_score,
            2,
        )

        return score, min(confidence, 1.0)

    def _classify_lifecycle(self, trend_name: str, signals: list[dict], score: float) -> str:
        """Classify lifecycle stage based on score thresholds."""
        thresholds = self.config["lifecycle_thresholds"]
        if score < thresholds["emerging"][1]:
            return "emerging"
        if score < thresholds["growing"][1]:
            return "growing"
        return "mature"

    def _detect_cross_industry(self, signals: list[dict]) -> bool:
        """Check if signals span 3+ industries."""
        industries = set()
        for s in signals:
            industries.update(s.get("industries", []))
        return len(industries) >= 3

    def predict(self, trends: list[dict], upcoming_shows: list[dict]) -> list[dict]:
        """Predict trend prominence at upcoming shows."""
        predictions = []
        for show in upcoming_shows:
            show_industries = set(show.get("industries", []))
            for trend in trends:
                trend_industries = set(trend.get("industries", []))
                relevance = len(trend_industries & show_industries) / max(len(show_industries), 1)
                if relevance > 0:
                    predicted_score = trend.get("composite_score", 0) * (0.7 + 0.3 * relevance)
                    predictions.append({
                        "trend_name": trend.get("name", ""),
                        "show_name": show.get("name", ""),
                        "predicted_score": round(predicted_score, 1),
                        "predicted_lifecycle": trend.get("lifecycle", "emerging"),
                        "industry_relevance": round(relevance, 2),
                    })
        return predictions

    def evaluate(self, predictions: list[dict], actuals: list[dict]) -> float:
        """Evaluate prediction accuracy against actual outcomes."""
        if not predictions or not actuals:
            return 0.0

        pred_map = {p["trend_name"]: p.get("predicted_score", 0) for p in predictions}
        actual_map = {a["trend_name"]: a.get("actual_score", 0) for a in actuals}
        common = set(pred_map) & set(actual_map)

        if not common:
            return 0.0

        total_error = sum(abs(pred_map[t] - actual_map[t]) / 100.0 for t in common)
        return round(max(1.0 - total_error / len(common), 0.0), 4)

    def get_config(self) -> dict:
        return copy.deepcopy(self.config)

    def update_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value

    def run_experiment(self) -> dict:
        """Run a single autoresearch experiment cycle.

        1. Pick a parameter to modify
        2. Run analysis with modified parameter
        3. Evaluate against baseline
        4. Keep or discard the change
        """
        # Save baseline config
        baseline_config = copy.deepcopy(self.config)
        signals = self._load_seed_signals()
        baseline_trends = self.analyze(signals)

        # Pick a random parameter to tweak
        param_choices = [
            ("clustering_threshold", random.uniform(0.5, 0.8)),
            ("momentum_weights.recency", random.uniform(0.2, 0.4)),
            ("momentum_weights.frequency", random.uniform(0.15, 0.35)),
            ("velocity_window", random.randint(2, 5)),
        ]
        param_name, new_value = random.choice(param_choices)

        # Apply modification
        if "." in param_name:
            outer, inner = param_name.split(".", 1)
            self.config[outer][inner] = new_value
        else:
            self.config[param_name] = new_value

        # Run analysis with modified config
        modified_trends = self.analyze(signals)

        # Evaluate (using baseline as "ground truth" for now)
        baseline_preds = [{"trend_name": t["name"], "predicted_score": t["composite_score"],
                           "predicted_lifecycle": t["lifecycle"]} for t in baseline_trends]
        modified_preds = [{"trend_name": t["name"], "predicted_score": t["composite_score"],
                           "predicted_lifecycle": t["lifecycle"]} for t in modified_trends]

        # Simple stability metric: how much did rankings change?
        baseline_ranking = [t["name"] for t in baseline_trends]
        modified_ranking = [t["name"] for t in modified_trends]
        common = set(baseline_ranking) & set(modified_ranking)
        if common:
            rank_diff = sum(
                abs(baseline_ranking.index(t) - modified_ranking.index(t)) for t in common
            ) / len(common)
            kept = rank_diff < 1.5  # Keep if rankings didn't shift too wildly
        else:
            kept = False

        if not kept:
            self.config = baseline_config

        result = {
            "param_modified": param_name,
            "new_value": new_value,
            "kept": kept,
            "rank_diff": rank_diff if common else float("inf"),
        }
        self._experiment_log.append(result)
        return result

    def _load_seed_trends(self) -> list[dict]:
        path = DATA_DIR / "trends.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _load_seed_signals(self) -> list[dict]:
        path = DATA_DIR / "signals.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []
