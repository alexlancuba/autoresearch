"""
SignalCollector — the data-gathering agent for trade show intelligence.

Autoresearch parallel
---------------------
In a traditional ML pipeline, this agent is analogous to a data loader combined
with a feature extractor.  Its "model" is the set of heuristics it uses to
decide *which* sources matter, *how* to parse them, *what* taxonomy to apply,
and *how fresh* data must be.  The ``run_experiment`` loop modifies these
parameters, re-runs collection, and keeps changes only when the downstream
``signal_yield_rate`` improves — mirroring how train.py would iterate on
hyperparameters and measure loss.

Modifiable parameters (the knobs ``run_experiment`` turns):
    source_weights        — dict[str, float] priority per source type
    extraction_prompts    — dict[str, str] prompt templates for parsing
    signal_taxonomy       — list[str] valid signal categories
    freshness_windows     — dict[str, int] lookback days per signal type
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import random
from datetime import datetime, timedelta
from typing import Optional

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# ── Defaults ────────────────────────────────────────────────────────────────

_DEFAULT_SOURCE_WEIGHTS: dict[str, float] = {
    "exhibitor_list": 0.70,
    "press_release": 0.65,
    "social_media": 0.40,
    "media_coverage": 0.80,
    "analyst_report": 0.90,
    "keynote_session": 0.85,
    "award": 0.60,
    "patent_filing": 0.75,
    "booth_photography": 0.35,
    "post_show_report": 0.80,
    "industry_publication": 0.70,
}

_DEFAULT_EXTRACTION_PROMPTS: dict[str, str] = {
    "media_coverage": (
        "Extract trade-show trend signals from this media article. "
        "For each signal, identify: the trend category, affected industries, "
        "geographic regions, and an estimated strength score (0-1)."
    ),
    "exhibitor_list": (
        "Analyze this exhibitor list and identify emerging product categories "
        "or technology themes that represent a year-over-year increase."
    ),
    "press_release": (
        "Parse this press release for concrete product or technology "
        "announcements that indicate directional trends."
    ),
    "keynote_session": (
        "Summarize the key forward-looking themes from this keynote. "
        "Focus on announced investments, partnerships, and product roadmaps."
    ),
    "post_show_report": (
        "Extract quantitative trend data from this post-show report, "
        "including exhibitor counts, attendance shifts, and category growth."
    ),
}

_DEFAULT_SIGNAL_TAXONOMY: list[str] = [
    "AI & Machine Learning",
    "Cybersecurity",
    "Digital Transformation",
    "Electric & Autonomous Vehicles",
    "Health Tech & Biotech",
    "Quantum Computing",
    "Robotics & Automation",
    "Spatial Computing & XR",
    "Supply Chain Innovation",
    "Sustainability & Green Tech",
]

_DEFAULT_FRESHNESS_WINDOWS: dict[str, int] = {
    "default": 180,
    "social_media": 30,
    "press_release": 90,
    "media_coverage": 120,
    "analyst_report": 365,
    "patent_filing": 365,
    "post_show_report": 180,
}


class SignalCollector:
    """Collects and scores raw trend signals from trade-show data sources.

    This agent owns the *input* side of the pipeline.  It reads seed data from
    JSON files, filters by scope parameters, scores each signal, and exposes
    its configuration for autonomous experimentation.
    """

    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.source_weights: dict[str, float] = config.get(
            "source_weights", copy.deepcopy(_DEFAULT_SOURCE_WEIGHTS)
        )
        self.extraction_prompts: dict[str, str] = config.get(
            "extraction_prompts", copy.deepcopy(_DEFAULT_EXTRACTION_PROMPTS)
        )
        self.signal_taxonomy: list[str] = config.get(
            "signal_taxonomy", list(_DEFAULT_SIGNAL_TAXONOMY)
        )
        self.freshness_windows: dict[str, int] = config.get(
            "freshness_windows", copy.deepcopy(_DEFAULT_FRESHNESS_WINDOWS)
        )

        # Internal tracking for eval
        self._total_signals_emitted: int = 0
        self._validated_signals: int = 0
        self._experiment_log: list[dict] = []

    # ── Public API ──────────────────────────────────────────────────────────

    def scan(
        self,
        scope: str = "full",
        industry: Optional[str] = None,
        region: Optional[str] = None,
        show: Optional[str] = None,
    ) -> list[dict]:
        """Load signals from seed data and filter by scope parameters.

        Parameters
        ----------
        scope : str
            One of ``"full"``, ``"regional"``, ``"show_specific"``, or
            ``"industry"``.
        industry : str, optional
            Filter to signals touching this industry.
        region : str, optional
            Filter to signals touching this region.
        show : str, optional
            Filter to signals from this trade show short-name.

        Returns
        -------
        list[dict]
            Signal dicts, each rescored using current ``source_weights``.
        """
        raw_signals = self._load_seed_signals()

        # Apply scope-based filtering
        filtered = raw_signals
        if industry:
            filtered = [
                s for s in filtered if industry in s.get("industries", [])
            ]
        if region:
            filtered = [
                s for s in filtered if region in s.get("regions", [])
            ]
        if show:
            filtered = [
                s for s in filtered if show in s.get("trade_shows", [])
            ]

        # Apply freshness window
        filtered = [s for s in filtered if self._is_fresh(s)]

        # Apply taxonomy filter — only keep signals whose category we recognize
        filtered = [
            s for s in filtered
            if s.get("trend_category", "") in self.signal_taxonomy
        ]

        # Re-extract and re-score using current config
        results = []
        for raw in filtered:
            extracted = self._extract_signals_from_source(
                raw.get("source_type", "media_coverage"), raw
            )
            for sig in extracted:
                sig["strength"] = self._score_signal_strength(
                    sig.get("text", ""),
                    sig.get("source_type", "media_coverage"),
                    sig.get("extracted_at", ""),
                )
                results.append(sig)

        self._total_signals_emitted += len(results)
        return results

    def _extract_signals_from_source(
        self, source_type: str, raw_data: dict
    ) -> list[dict]:
        """Apply the extraction prompt for *source_type* to raw data.

        In production this would call an LLM with the configured prompt.
        For seed-data mode, the signal is already structured so we pass it
        through with minor enrichment.

        Returns
        -------
        list[dict]
            Typically a single-element list (one signal per raw record).
        """
        # The extraction prompt that *would* be sent to an LLM
        _prompt = self.extraction_prompts.get(
            source_type,
            self.extraction_prompts.get(
                "media_coverage", "Extract trend signals."
            ),
        )
        # In seed-data mode the signal is pre-structured.
        signal = dict(raw_data)
        signal["_extraction_prompt_used"] = _prompt
        return [signal]

    def _score_signal_strength(
        self, signal_text: str, source_type: str, recency: str
    ) -> float:
        """Compute a 0-1 strength score for a signal.

        The score blends:
          * source weight (from ``source_weights`` config)
          * text heuristic  (length / keyword density as a proxy)
          * recency decay   (signals lose value over time)
        """
        # Source weight component
        source_w = self.source_weights.get(source_type, 0.5)

        # Text heuristic — longer, more specific text scores higher
        text_len = len(signal_text)
        text_score = min(text_len / 200.0, 1.0)

        # Recency decay
        recency_score = 1.0
        if recency:
            try:
                sig_dt = datetime.fromisoformat(recency)
                age_days = (datetime.utcnow() - sig_dt).days
                window = self.freshness_windows.get(
                    source_type,
                    self.freshness_windows.get("default", 180),
                )
                if age_days > window:
                    recency_score = 0.0
                else:
                    recency_score = max(0.0, 1.0 - (age_days / (window * 1.5)))
            except (ValueError, TypeError):
                recency_score = 0.5

        # Weighted composite
        score = 0.45 * source_w + 0.25 * text_score + 0.30 * recency_score
        return round(min(max(score, 0.0), 1.0), 4)

    # ── Config interface (what the agent can modify) ────────────────────────

    def get_config(self) -> dict:
        """Return a snapshot of all modifiable parameters."""
        return {
            "source_weights": dict(self.source_weights),
            "extraction_prompts": dict(self.extraction_prompts),
            "signal_taxonomy": list(self.signal_taxonomy),
            "freshness_windows": dict(self.freshness_windows),
        }

    def update_config(self, **kwargs) -> None:
        """Update one or more modifiable parameters.

        Accepted keyword arguments: ``source_weights``, ``extraction_prompts``,
        ``signal_taxonomy``, ``freshness_windows``.
        """
        for key in ("source_weights", "extraction_prompts",
                     "signal_taxonomy", "freshness_windows"):
            if key in kwargs:
                setattr(self, key, kwargs[key])

    # ── Eval metric ─────────────────────────────────────────────────────────

    @property
    def signal_yield_rate(self) -> float:
        """Percentage of emitted signals that were validated by TrendAnalyzer.

        This is the primary eval metric for the collector.  Higher is better:
        it means the collector is sending fewer false positives downstream.
        """
        if self._total_signals_emitted == 0:
            return 0.0
        return self._validated_signals / self._total_signals_emitted

    def record_validation(self, total_emitted: int, validated: int) -> None:
        """Called after TrendAnalyzer consumes signals to update yield stats."""
        self._total_signals_emitted += total_emitted
        self._validated_signals += validated

    # ── Autoresearch loop ───────────────────────────────────────────────────

    def run_experiment(self) -> dict:
        """Modify a parameter, re-run collection, evaluate, keep or discard.

        This is the ``train.py`` equivalent.  Each call:
          1. Snapshots current config and metric.
          2. Makes a random perturbation to one parameter.
          3. Re-runs ``scan()`` and measures the proxy eval metric.
          4. Keeps the change only if the metric improved.

        Returns
        -------
        dict
            Experiment log entry with before/after metrics and decision.
        """
        # Snapshot
        old_config = self.get_config()
        old_metric = self._proxy_eval()

        # Perturb a random source weight by +/- 10%
        source_type = random.choice(list(self.source_weights.keys()))
        old_val = self.source_weights[source_type]
        delta = random.uniform(-0.10, 0.10)
        new_val = min(max(old_val + delta, 0.0), 1.0)
        self.source_weights[source_type] = round(new_val, 4)

        change_desc = (
            f"source_weights[{source_type}]: {old_val:.4f} -> {new_val:.4f}"
        )

        # Re-evaluate
        new_metric = self._proxy_eval()

        kept = new_metric >= old_metric
        if not kept:
            # Revert
            self.source_weights = old_config["source_weights"]

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

    def _load_seed_signals(self) -> list[dict]:
        """Read signals from the seed data JSON file."""
        path = DATA_DIR / "signals.json"
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _is_fresh(self, signal: dict) -> bool:
        """Check whether a signal falls within its freshness window."""
        extracted = signal.get("extracted_at", "")
        if not extracted:
            return True
        try:
            sig_dt = datetime.fromisoformat(extracted)
            source = signal.get("source_type", "default")
            window = self.freshness_windows.get(
                source, self.freshness_windows.get("default", 180)
            )
            return (datetime.utcnow() - sig_dt).days <= window
        except (ValueError, TypeError):
            return True

    def _proxy_eval(self) -> float:
        """A self-contained proxy metric for experiment evaluation.

        Since we don't have a real TrendAnalyzer in the loop during
        ``run_experiment``, we use a proxy: the average signal strength
        of a full scan weighted by taxonomy coverage.
        """
        signals = self.scan()
        if not signals:
            return 0.0

        avg_strength = sum(s.get("strength", 0) for s in signals) / len(signals)
        categories_found = len({s.get("trend_category") for s in signals})
        taxonomy_coverage = categories_found / max(len(self.signal_taxonomy), 1)

        # Proxy: balance strength with breadth
        return 0.6 * avg_strength + 0.4 * taxonomy_coverage
