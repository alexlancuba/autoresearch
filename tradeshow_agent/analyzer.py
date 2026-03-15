"""Trend analysis engine for trade show data.

Aggregates trend signals, computes cross-industry and cross-regional patterns,
scores trends, and identifies emerging opportunities.
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from .researcher import TrendSignal

logger = logging.getLogger(__name__)


@dataclass
class TrendSummary:
    """Aggregated trend with cross-source scoring."""
    title: str
    description: str
    score: float  # Composite score (higher = more significant)
    signal_type: str
    industries: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    source_events: list[str] = field(default_factory=list)
    total_mentions: int = 0
    avg_confidence: float = 0.0
    all_keywords: list[str] = field(default_factory=list)
    is_cross_industry: bool = False
    is_global: bool = False


@dataclass
class IndustryInsight:
    """Insight specific to an industry."""
    industry: str
    top_trends: list[TrendSummary]
    active_shows: list[str]
    trend_direction: str  # "accelerating", "stable", "shifting"
    key_theme: str


@dataclass
class RegionalInsight:
    """Insight specific to a geographic region."""
    region: str
    top_trends: list[TrendSummary]
    dominant_industries: list[str]
    emerging_hubs: list[str]
    market_sentiment: str  # "bullish", "neutral", "cautious"


@dataclass
class AnalysisReport:
    """Complete analysis report."""
    timestamp: str
    global_trends: list[TrendSummary]
    industry_insights: list[IndustryInsight]
    regional_insights: list[RegionalInsight]
    cross_industry_themes: list[TrendSummary]
    emerging_opportunities: list[str]
    total_signals_analyzed: int = 0
    total_events_covered: int = 0


class TrendAnalyzer:
    """Analyzes and aggregates trade show trend signals."""

    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    def analyze(self, signals: list[TrendSignal]) -> AnalysisReport:
        """Run full analysis on collected trend signals."""
        logger.info(f"Analyzing {len(signals)} trend signals")

        # Aggregate signals into summaries
        summaries = self._aggregate_signals(signals)

        # Score and rank
        scored = self._score_trends(summaries)

        # Generate industry insights
        industry_insights = self._industry_analysis(signals, scored)

        # Generate regional insights
        regional_insights = self._regional_analysis(signals, scored)

        # Identify cross-industry themes
        cross_industry = [s for s in scored if s.is_cross_industry]

        # Identify emerging opportunities
        emerging = self._identify_opportunities(scored, signals)

        # Count unique events
        all_events = set()
        for s in signals:
            all_events.add(s.source_event)

        return AnalysisReport(
            timestamp=datetime.utcnow().isoformat(),
            global_trends=scored[:self.top_n],
            industry_insights=industry_insights,
            regional_insights=regional_insights,
            cross_industry_themes=cross_industry[:5],
            emerging_opportunities=emerging,
            total_signals_analyzed=len(signals),
            total_events_covered=len(all_events),
        )

    def _aggregate_signals(self, signals: list[TrendSignal]) -> list[TrendSummary]:
        """Group signals by trend title and aggregate."""
        grouped = defaultdict(list)
        for signal in signals:
            grouped[signal.title].append(signal)

        summaries = []
        for title, group in grouped.items():
            industries = list(set(s.industry for s in group))
            regions = list(set(s.region for s in group))
            events = list(set(s.source_event for s in group))
            all_keywords = list(set(kw for s in group for kw in s.keywords))
            avg_conf = sum(s.confidence for s in group) / len(group)

            # Determine dominant signal type
            type_counts = Counter(s.signal_type for s in group)
            dominant_type = type_counts.most_common(1)[0][0]

            # Build consolidated description
            descriptions = set(s.description for s in group)
            consolidated_desc = next(iter(descriptions))
            if len(descriptions) > 1:
                consolidated_desc += f" (Observed across {len(events)} trade shows in {len(regions)} regions.)"

            summary = TrendSummary(
                title=title,
                description=consolidated_desc,
                score=0.0,  # Will be computed in scoring step
                signal_type=dominant_type,
                industries=industries,
                regions=regions,
                source_events=events,
                total_mentions=len(group),
                avg_confidence=round(avg_conf, 3),
                all_keywords=all_keywords[:15],
                is_cross_industry=len(industries) >= 3,
                is_global=len(regions) >= 3,
            )
            summaries.append(summary)

        return summaries

    def _score_trends(self, summaries: list[TrendSummary]) -> list[TrendSummary]:
        """Score trends based on multiple factors."""
        for s in summaries:
            score = 0.0

            # Frequency score: more mentions = higher score
            score += min(s.total_mentions * 2.0, 20.0)

            # Confidence score
            score += s.avg_confidence * 10.0

            # Cross-industry bonus
            score += len(s.industries) * 3.0

            # Global reach bonus
            score += len(s.regions) * 4.0

            # Signal type weighting
            type_weights = {
                "emerging": 5.0,
                "growing": 3.0,
                "mature": 1.0,
                "declining": -2.0,
            }
            score += type_weights.get(s.signal_type, 0.0)

            # Source diversity bonus
            score += min(len(s.source_events) * 1.5, 15.0)

            s.score = round(score, 2)

        summaries.sort(key=lambda x: x.score, reverse=True)
        return summaries

    def _industry_analysis(self, signals: list[TrendSignal],
                           scored: list[TrendSummary]) -> list[IndustryInsight]:
        """Generate per-industry insights."""
        industry_signals = defaultdict(list)
        for s in signals:
            industry_signals[s.industry].append(s)

        insights = []
        for industry, ind_signals in industry_signals.items():
            # Get relevant scored trends
            relevant_trends = [
                t for t in scored
                if industry in t.industries
            ][:5]

            # Active shows
            active_shows = list(set(s.source_event for s in ind_signals))

            # Determine direction
            type_counts = Counter(s.signal_type for s in ind_signals)
            if type_counts.get("emerging", 0) + type_counts.get("growing", 0) > len(ind_signals) * 0.6:
                direction = "accelerating"
            elif type_counts.get("declining", 0) > len(ind_signals) * 0.3:
                direction = "shifting"
            else:
                direction = "stable"

            # Key theme
            all_keywords = [kw for s in ind_signals for kw in s.keywords]
            key_theme = Counter(all_keywords).most_common(1)[0][0] if all_keywords else "general"

            insights.append(IndustryInsight(
                industry=industry,
                top_trends=relevant_trends,
                active_shows=active_shows,
                trend_direction=direction,
                key_theme=key_theme,
            ))

        # Sort by number of signals (most active industries first)
        insights.sort(key=lambda x: len(x.top_trends), reverse=True)
        return insights

    def _regional_analysis(self, signals: list[TrendSignal],
                           scored: list[TrendSummary]) -> list[RegionalInsight]:
        """Generate per-region insights."""
        region_signals = defaultdict(list)
        for s in signals:
            region_signals[s.region].append(s)

        insights = []
        for region, reg_signals in region_signals.items():
            relevant_trends = [
                t for t in scored
                if region in t.regions
            ][:5]

            # Dominant industries
            ind_counts = Counter(s.industry for s in reg_signals)
            dominant = [ind for ind, _ in ind_counts.most_common(3)]

            # Market sentiment based on signal types
            growing = sum(1 for s in reg_signals if s.signal_type in ("emerging", "growing"))
            ratio = growing / len(reg_signals) if reg_signals else 0
            if ratio > 0.7:
                sentiment = "bullish"
            elif ratio > 0.4:
                sentiment = "neutral"
            else:
                sentiment = "cautious"

            insights.append(RegionalInsight(
                region=region,
                top_trends=relevant_trends,
                dominant_industries=dominant,
                emerging_hubs=[],
                market_sentiment=sentiment,
            ))

        return insights

    def _identify_opportunities(self, scored: list[TrendSummary],
                                signals: list[TrendSignal]) -> list[str]:
        """Identify emerging opportunities from trend patterns."""
        opportunities = []

        # Emerging trends with cross-industry appeal
        for trend in scored:
            if trend.signal_type == "emerging" and trend.is_cross_industry:
                opportunities.append(
                    f"Cross-industry emerging trend: '{trend.title}' is gaining traction "
                    f"across {', '.join(trend.industries[:3])} "
                    f"in {', '.join(trend.regions[:3])}."
                )

        # Growing trends that are becoming global
        for trend in scored:
            if trend.signal_type == "growing" and trend.is_global and trend.total_mentions >= 3:
                opportunities.append(
                    f"Scaling globally: '{trend.title}' is expanding worldwide with "
                    f"{trend.total_mentions} mentions across {len(trend.regions)} regions."
                )

        # Region-specific emerging themes
        region_emerging = defaultdict(list)
        for s in signals:
            if s.signal_type == "emerging":
                region_emerging[s.region].append(s.title)

        for region, titles in region_emerging.items():
            unique_titles = list(set(titles))
            if len(unique_titles) >= 2:
                opportunities.append(
                    f"Emerging cluster in {region}: {', '.join(unique_titles[:3])} "
                    f"are emerging themes in this region's trade shows."
                )

        return opportunities[:10]

    def signals_to_dataframe(self, signals: list[TrendSignal]) -> pd.DataFrame:
        """Convert signals to a pandas DataFrame for additional analysis."""
        records = []
        for s in signals:
            records.append({
                "title": s.title,
                "industry": s.industry,
                "region": s.region,
                "source_event": s.source_event,
                "signal_type": s.signal_type,
                "confidence": s.confidence,
                "keywords": ", ".join(s.keywords),
                "fetched_at": s.fetched_at,
            })
        return pd.DataFrame(records)
