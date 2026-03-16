"""
TrendAnalyzer — the analysis engine for trade show intelligence.

Autoresearch parallel
---------------------
This agent is the "model" in the ML sense.  It takes signals (features) and
produces trends (predictions).  Its modifiable parameters — clustering
thresholds, momentum weights, confidence weights, lifecycle thresholds,
regional weights, and velocity windows — are the hyperparameters that
``run_experiment`` tunes.  The ``evaluate`` method computes an accuracy score
that serves as the loss function, and the agent only keeps parameter changes
that improve this score.

The cycle mirrors train.py:
    1. Snapshot current parameters and eval metric.
    2. Perturb one parameter.
    3. Re-run analysis and scoring.
    4. Keep if metric improved, revert if not.
"""

from __future__ import annotations

import copy
import json
import math
import os
import pathlib
import random
from collections import defaultdict
from datetime import datetime
from typing import Optional

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# ── Defaults ────────────────────────────────────────────────────────────────

_DEFAULT_CLUSTERING_THRESHOLD: float = 0.55

_DEFAULT_MOMENTUM_WEIGHTS: dict[str, float] = {
    "recency": 0.30,
    "frequency": 0.25,
    "geographic_spread": 0.20,
    "industry_breadth": 0.25,
}

_DEFAULT_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "signal_count": 0.40,
    "source_diversity": 0.35,
    "cross_validation": 0.25,
}

_DEFAULT_LIFECYCLE_THRESHOLDS: dict[str, tuple[float, float]] = {
    "emerging": (0.0, 40.0),
    "growing": (40.0, 70.0),
    "mature": (70.0, 90.0),
    "declining": (90.0, 100.0),
}

_DEFAULT_REGIONAL_WEIGHTS: dict[str, float] = {
    "North America": 1.0,
    "Europe": 0.95,
    "Asia-Pacific": 0.90,
    "Middle East & Africa": 0.75,
    "Latin America": 0.70,
}

_DEFAULT_VELOCITY_WINDOW: int = 3  # cycles


class TrendAnalyzer:
    """Clusters signals into trends, scores them, and generates predictions.

    This agent owns the *analysis* layer.  It consumes signals from
    ``SignalCollector``, groups them into named trends, assigns composite
    scores and confidence values, classifies lifecycle stages, and can
    produce forward-looking predictions for upcoming trade shows.
    """

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.clustering_threshold: float = config.get(
            "clustering_threshold", _DEFAULT_CLUSTERING_THRESHOLD
        )
        self.momentum_weights: dict[str, float] = config.get(
            "momentum_weights", copy.deepcopy(_DEFAULT_MOMENTUM_WEIGHTS)
        )
        self.confidence_weights: dict[str, float] = config.get(
            "confidence_weights", copy.deepcopy(_DEFAULT_CONFIDENCE_WEIGHTS)
        )
        self.lifecycle_thresholds: dict[str, tuple[float, float]] = config.get(
            "lifecycle_thresholds", copy.deepcopy(_DEFAULT_LIFECYCLE_THRESHOLDS)
        )
        self.regional_weights: dict[str, float] = config.get(
            "regional_weights", copy.deepcopy(_DEFAULT_REGIONAL_WEIGHTS)
        )
        self.velocity_window: int = config.get(
            "velocity_window", _DEFAULT_VELOCITY_WINDOW
        )

        # Internal tracking
        self._experiment_log: list[dict] = []
        self._last_predictions: list[dict] = []

    # ── Public API ──────────────────────────────────────────────────────────

    def analyze(
        self,
        signals: list[dict],
        industry: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[dict]:
        """Produce a ranked list of trends from a set of signals.

        If signals are provided, actual clustering and scoring logic runs.
        The seed trends from ``data/trends.json`` serve as a baseline that
        is enriched with live analysis when signals are available.

        Parameters
        ----------
        signals : list[dict]
            Signal dicts (output of ``SignalCollector.scan``).
        industry : str, optional
            Filter results to trends touching this industry.
        region : str, optional
            Filter results to trends touching this region.

        Returns
        -------
        list[dict]
            Trend dicts sorted by composite_score descending.
        """
        # Cluster the incoming signals into named groups
        clusters = self._cluster_signals(signals)

        # Load baseline trends for enrichment
        baseline = self._load_seed_trends()
        baseline_by_name = {t["name"]: t for t in baseline}

        trends: list[dict] = []
        for trend_name, cluster_signals in clusters.items():
            score, confidence = self._score_trend(trend_name, cluster_signals)
            lifecycle = self._classify_lifecycle(
                trend_name, cluster_signals, score
            )
            cross_industry = self._detect_cross_industry(cluster_signals)

            # Merge with baseline if available
            base = baseline_by_name.get(trend_name, {})

            trend = {
                "id": base.get(
                    "id", f"trend-{abs(hash(trend_name)) % 10000:04d}"
                ),
                "rank": 0,  # assigned after sorting
                "name": trend_name,
                "description": base.get(
                    "description", f"Trend cluster: {trend_name}"
                ),
                "lifecycle": lifecycle,
                "composite_score": round(score, 2),
                "confidence": round(confidence, 4),
                "industries": self._collect_field(
                    cluster_signals, "industries"
                ),
                "regions": self._collect_field(cluster_signals, "regions"),
                "cross_industry": cross_industry,
                "scope": self._determine_scope(cluster_signals),
                "signal_ids": [s.get("id", "") for s in cluster_signals],
                "signal_count": len(cluster_signals),
                "mention_count": base.get(
                    "mention_count", len(cluster_signals)
                ),
                "show_count": len(
                    self._collect_field(cluster_signals, "trade_shows")
                ),
                "keywords": base.get("keywords", [trend_name.lower()]),
                "velocity": base.get("velocity", 0.0),
                "prediction": base.get("prediction", ""),
                "design_implications": base.get("design_implications", ""),
                "cycle_id": base.get("cycle_id", ""),
            }
            trends.append(trend)

        # Also include baseline trends that had no matching signals
        seen_names = {t["name"] for t in trends}
        for bt in baseline:
            if bt["name"] not in seen_names:
                trends.append(bt)

        # Filter
        if industry:
            trends = [
                t for t in trends if industry in t.get("industries", [])
            ]
        if region:
            trends = [
                t for t in trends if region in t.get("regions", [])
            ]

        # Sort and assign ranks
        trends.sort(key=lambda t: t.get("composite_score", 0), reverse=True)
        for i, t in enumerate(trends, 1):
            t["rank"] = i

        return trends

    def _cluster_signals(self, signals: list[dict]) -> dict[str, list[dict]]:
        """Group signals by trend_category.

        In production this would use embedding similarity with the configured
        ``clustering_threshold``.  For seed-data mode we cluster on the
        ``trend_category`` field directly, applying the threshold as a
        minimum strength filter.
        """
        clusters: dict[str, list[dict]] = defaultdict(list)
        for sig in signals:
            category = sig.get("trend_category", "Uncategorized")
            strength = sig.get("strength", 0.0)
            # Only include signals above the clustering threshold
            if strength >= self.clustering_threshold:
                clusters[category].append(sig)
        return dict(clusters)

    def _score_trend(
        self, trend_name: str, signals: list[dict]
    ) -> tuple[float, float]:
        """Compute a composite score (0-100) and confidence (0-1) for a trend.

        The composite score uses ``momentum_weights``:
          * recency     — how recent the signals are
          * frequency   — how many signals
          * geographic_spread — number of distinct regions
          * industry_breadth  — number of distinct industries

        Confidence uses ``confidence_weights``:
          * signal_count    — more signals = higher confidence
          * source_diversity — more source types = higher confidence
          * cross_validation — signals from multiple shows
        """
        if not signals:
            return (0.0, 0.0)

        mw = self.momentum_weights
        cw = self.confidence_weights

        # ── Momentum components ─────────────────────────────────────────
        # Recency: average days-ago, normalized to 0-1 (0 = old, 1 = recent)
        now = datetime.utcnow()
        ages = []
        for s in signals:
            try:
                dt = datetime.fromisoformat(s.get("extracted_at", ""))
                ages.append((now - dt).days)
            except (ValueError, TypeError):
                ages.append(180)
        avg_age = sum(ages) / len(ages) if ages else 180
        recency_score = max(0.0, 1.0 - avg_age / 365.0)

        # Frequency: log-scaled signal count
        frequency_score = min(1.0, math.log2(len(signals) + 1) / 4.0)

        # Geographic spread
        all_regions: set[str] = set()
        for s in signals:
            all_regions.update(s.get("regions", []))
        geo_score = min(1.0, len(all_regions) / 5.0)

        # Industry breadth
        all_industries: set[str] = set()
        for s in signals:
            all_industries.update(s.get("industries", []))
        ind_score = min(1.0, len(all_industries) / 5.0)

        composite = (
            mw.get("recency", 0.25) * recency_score
            + mw.get("frequency", 0.25) * frequency_score
            + mw.get("geographic_spread", 0.25) * geo_score
            + mw.get("industry_breadth", 0.25) * ind_score
        ) * 100.0

        # Apply regional weight boost
        for r in all_regions:
            rw = self.regional_weights.get(r, 0.8)
            composite *= 0.9 + 0.1 * rw  # mild boost per region

        composite = min(composite, 100.0)

        # ── Confidence components ───────────────────────────────────────
        # Signal count confidence
        count_conf = min(1.0, len(signals) / 10.0)

        # Source diversity
        source_types = {s.get("source_type", "") for s in signals}
        diversity_conf = min(1.0, len(source_types) / 5.0)

        # Cross-validation (signals from multiple shows)
        shows: set[str] = set()
        for s in signals:
            shows.update(s.get("trade_shows", []))
        cross_conf = min(1.0, len(shows) / 3.0)

        confidence = (
            cw.get("signal_count", 0.4) * count_conf
            + cw.get("source_diversity", 0.35) * diversity_conf
            + cw.get("cross_validation", 0.25) * cross_conf
        )

        return (composite, confidence)

    def _classify_lifecycle(
        self, trend_name: str, signals: list[dict], score: float
    ) -> str:
        """Assign a lifecycle stage based on composite score and thresholds."""
        for stage, bounds in self.lifecycle_thresholds.items():
            lo, hi = bounds
            if lo <= score < hi:
                return stage
        # Default to growing if score is exactly at a boundary
        return "growing"

    def _detect_cross_industry(self, signals: list[dict]) -> bool:
        """Return True if signals span 3+ distinct industries."""
        all_industries: set[str] = set()
        for s in signals:
            all_industries.update(s.get("industries", []))
        return len(all_industries) >= 3

    def predict(
        self, trends: list[dict], upcoming_shows: list[dict]
    ) -> list[dict]:
        """Generate predictions for how trends will manifest at upcoming shows.

        Parameters
        ----------
        trends : list[dict]
            Current trend analysis output.
        upcoming_shows : list[dict]
            Dicts with at least ``name``, ``industries``, ``region``.

        Returns
        -------
        list[dict]
            Predictions with ``show_name``, ``trend_name``,
            ``expected_strength``, and ``rationale``.
        """
        predictions: list[dict] = []
        for show in upcoming_shows:
            show_industries = set(show.get("industries", []))
            show_region = show.get("region", "")
            for trend in trends:
                trend_industries = set(trend.get("industries", []))
                overlap = show_industries & trend_industries
                if not overlap:
                    continue

                # Predict strength based on composite score, velocity, and
                # regional relevance
                base = trend.get("composite_score", 0) / 100.0
                velocity_boost = trend.get("velocity", 0) * 0.2
                region_boost = (
                    0.1
                    if show_region in trend.get("regions", [])
                    else -0.05
                )
                expected = min(
                    1.0, max(0.0, base + velocity_boost + region_boost)
                )

                predictions.append({
                    "show_name": show.get("name", ""),
                    "trend_name": trend.get("name", ""),
                    "expected_strength": round(expected, 4),
                    "lifecycle": trend.get("lifecycle", ""),
                    "overlapping_industries": sorted(overlap),
                    "rationale": (
                        f"{trend['name']} (score "
                        f"{trend.get('composite_score', 0):.1f}, "
                        f"velocity {trend.get('velocity', 0):.2f}) is "
                        f"{'regionally relevant' if show_region in trend.get('regions', []) else 'expanding to new region'} "
                        f"for {show.get('name', '')}."
                    ),
                })

        predictions.sort(
            key=lambda p: p["expected_strength"], reverse=True
        )
        self._last_predictions = predictions
        return predictions

    def evaluate(
        self, predictions: list[dict], actuals: list[dict]
    ) -> float:
        """Compute prediction accuracy by comparing predictions to actuals.

        Uses mean absolute error between predicted and actual strength values,
        converted to an accuracy score (1 - MAE).

        Parameters
        ----------
        predictions : list[dict]
            Previously generated predictions (from ``predict``).
        actuals : list[dict]
            Dicts with ``show_name``, ``trend_name``, ``actual_strength``.

        Returns
        -------
        float
            Accuracy score between 0.0 and 1.0.
        """
        if not predictions or not actuals:
            return 0.0

        # Build lookup for actuals
        actual_lookup: dict[tuple[str, str], float] = {}
        for a in actuals:
            key = (a.get("show_name", ""), a.get("trend_name", ""))
            actual_lookup[key] = a.get("actual_strength", 0.0)

        errors: list[float] = []
        for p in predictions:
            key = (p.get("show_name", ""), p.get("trend_name", ""))
            if key in actual_lookup:
                err = abs(
                    p.get("expected_strength", 0) - actual_lookup[key]
                )
                errors.append(err)

        if not errors:
            return 0.0

        mae = sum(errors) / len(errors)
        return round(max(0.0, 1.0 - mae), 4)

    # ── Config interface ────────────────────────────────────────────────────

    def get_config(self) -> dict:
        """Return a snapshot of all modifiable parameters."""
        return {
            "clustering_threshold": self.clustering_threshold,
            "momentum_weights": dict(self.momentum_weights),
            "confidence_weights": dict(self.confidence_weights),
            "lifecycle_thresholds": {
                k: list(v) for k, v in self.lifecycle_thresholds.items()
            },
            "regional_weights": dict(self.regional_weights),
            "velocity_window": self.velocity_window,
        }

    def update_config(self, **kwargs) -> None:
        """Update one or more modifiable parameters.

        Accepted keyword arguments: ``clustering_threshold``,
        ``momentum_weights``, ``confidence_weights``,
        ``lifecycle_thresholds``, ``regional_weights``, ``velocity_window``.
        """
        for key in (
            "clustering_threshold",
            "momentum_weights",
            "confidence_weights",
            "lifecycle_thresholds",
            "regional_weights",
            "velocity_window",
        ):
            if key in kwargs:
                setattr(self, key, kwargs[key])

    # ── Autoresearch loop ───────────────────────────────────────────────────

    def run_experiment(self) -> dict:
        """Modify a parameter, re-run analysis, evaluate, keep or discard.

        Each call:
          1. Snapshots current config and proxy metric.
          2. Perturbs one momentum or confidence weight.
          3. Re-runs analysis on seed signals and measures quality.
          4. Keeps the change only if metric improved.

        Returns
        -------
        dict
            Experiment log entry.
        """
        old_config = self.get_config()
        old_metric = self._proxy_eval()

        # Choose what to perturb
        target = random.choice([
            "momentum_weights",
            "confidence_weights",
            "clustering_threshold",
        ])

        if target == "clustering_threshold":
            old_val = self.clustering_threshold
            delta = random.uniform(-0.05, 0.05)
            self.clustering_threshold = round(
                min(max(old_val + delta, 0.1), 0.9), 4
            )
            change_desc = (
                f"clustering_threshold: {old_val:.4f} -> "
                f"{self.clustering_threshold:.4f}"
            )
        else:
            weights = getattr(self, target)
            key = random.choice(list(weights.keys()))
            old_val = weights[key]
            delta = random.uniform(-0.05, 0.05)
            weights[key] = round(min(max(old_val + delta, 0.0), 1.0), 4)
            change_desc = (
                f"{target}[{key}]: {old_val:.4f} -> {weights[key]:.4f}"
            )

        new_metric = self._proxy_eval()

        kept = new_metric >= old_metric
        if not kept:
            # Revert all parameters
            self.clustering_threshold = old_config["clustering_threshold"]
            self.momentum_weights = old_config["momentum_weights"]
            self.confidence_weights = old_config["confidence_weights"]

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "change": change_desc,
            "metric_before": round(old_metric, 4),
            "metric_after": round(new_metric, 4),
            "kept": kept,
        }
        self._experiment_log.append(entry)
        return entry

    # ── Internal helpers ────────────────────────────────────────────────────

    def _load_seed_trends(self) -> list[dict]:
        """Read trends from seed data JSON."""
        path = DATA_DIR / "trends.json"
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_seed_signals(self) -> list[dict]:
        """Read signals from seed data JSON (for proxy eval)."""
        path = DATA_DIR / "signals.json"
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _collect_field(signals: list[dict], field: str) -> list[str]:
        """Collect unique values from a list-valued field across signals."""
        values: set[str] = set()
        for s in signals:
            val = s.get(field, [])
            if isinstance(val, list):
                values.update(val)
            elif isinstance(val, str):
                values.add(val)
        return sorted(values)

    @staticmethod
    def _determine_scope(signals: list[dict]) -> str:
        """Determine geographic scope from signals."""
        all_regions: set[str] = set()
        for s in signals:
            all_regions.update(s.get("regions", []))
        if len(all_regions) >= 3:
            return "Global"
        elif len(all_regions) == 1:
            return next(iter(all_regions))
        else:
            return "Multi-regional"

    def _proxy_eval(self) -> float:
        """Self-contained proxy metric for experiment evaluation.

        Runs full analysis on seed signals and measures:
          * trend coverage (how many distinct trends are produced)
          * score spread  (variance in scores — more spread = better
            differentiation)
          * confidence average
        """
        seed_signals = self._load_seed_signals()
        trends = self.analyze(seed_signals)

        if not trends:
            return 0.0

        # Coverage: fraction of seed trends found
        seed_trends = self._load_seed_trends()
        coverage = len(trends) / max(len(seed_trends), 1)

        # Score spread: standard deviation of composite scores
        scores = [t.get("composite_score", 0) for t in trends]
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        spread = math.sqrt(variance) / 100.0  # normalize

        # Average confidence
        avg_conf = sum(t.get("confidence", 0) for t in trends) / len(trends)

        return 0.4 * min(coverage, 1.0) + 0.3 * spread + 0.3 * avg_conf
