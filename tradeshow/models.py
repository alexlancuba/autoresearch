"""
Data models for the Trade Show Trend Analysis system.

These models represent the structural backbone shared by all three agents:
SignalCollector, TrendAnalyzer, and ReportGenerator.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Enums ────────────────────────────────────────────────────────────────────


class Industry(str, Enum):
    TECHNOLOGY_ELECTRONICS = "Technology & Electronics"
    HEALTHCARE_MEDICAL = "Healthcare & Medical Devices"
    AUTOMOTIVE_TRANSPORTATION = "Automotive & Transportation"
    FOOD_BEVERAGE = "Food & Beverage"
    ENERGY_SUSTAINABILITY = "Energy & Sustainability"
    FASHION_TEXTILES = "Fashion & Textiles"
    CONSTRUCTION_REAL_ESTATE = "Construction & Real Estate"
    AGRICULTURE_FARMING = "Agriculture & Farming"
    DEFENSE_AEROSPACE = "Defense & Aerospace"
    RETAIL_ECOMMERCE = "Retail & E-Commerce"
    MANUFACTURING_INDUSTRIAL = "Manufacturing & Industrial"
    TELECOMMUNICATIONS = "Telecommunications"
    ENTERTAINMENT_MEDIA = "Entertainment & Media"
    LOGISTICS_SUPPLY_CHAIN = "Logistics & Supply Chain"
    FINANCE_FINTECH = "Finance & Fintech"


class Region(str, Enum):
    NORTH_AMERICA = "North America"
    EUROPE = "Europe"
    ASIA_PACIFIC = "Asia-Pacific"
    MIDDLE_EAST_AFRICA = "Middle East & Africa"
    LATIN_AMERICA = "Latin America"


class LifecycleStage(str, Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    MATURE = "mature"
    DECLINING = "declining"


class ShowTier(str, Enum):
    GLOBAL_FLAGSHIP = "global_flagship"
    REGIONAL_MAJOR = "regional_major"
    NICHE = "niche"


class SignalSourceType(str, Enum):
    EXHIBITOR_LIST = "exhibitor_list"
    PRESS_RELEASE = "press_release"
    SOCIAL_MEDIA = "social_media"
    MEDIA_COVERAGE = "media_coverage"
    ANALYST_REPORT = "analyst_report"
    KEYNOTE_SESSION = "keynote_session"
    AWARD = "award"
    PATENT_FILING = "patent_filing"
    BOOTH_PHOTOGRAPHY = "booth_photography"
    POST_SHOW_REPORT = "post_show_report"
    INDUSTRY_PUBLICATION = "industry_publication"


# ── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class TradeShow:
    """A trade show event in the global database."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    short_name: str = ""  # e.g., "CES", "MWC", "MEDICA"
    industries: list[Industry] = field(default_factory=list)
    region: Region = Region.NORTH_AMERICA
    city: str = ""
    country: str = ""
    frequency: str = "annual"  # annual, biennial, etc.
    tier: ShowTier = ShowTier.REGIONAL_MAJOR
    typical_exhibitors: int = 0
    typical_attendees: int = 0
    next_date: Optional[str] = None  # ISO date
    website: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "industries": [i.value for i in self.industries],
            "region": self.region.value,
            "city": self.city,
            "country": self.country,
            "frequency": self.frequency,
            "tier": self.tier.value,
            "typical_exhibitors": self.typical_exhibitors,
            "typical_attendees": self.typical_attendees,
            "next_date": self.next_date,
            "website": self.website,
        }


@dataclass
class Signal:
    """A raw observation extracted from trade show data sources."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    source_url: str = ""
    source_type: SignalSourceType = SignalSourceType.MEDIA_COVERAGE
    trade_shows: list[str] = field(default_factory=list)  # show short_names
    industries: list[Industry] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    trend_category: str = ""
    strength: float = 0.0  # 0-1
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cycle_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "source_url": self.source_url,
            "source_type": self.source_type.value,
            "trade_shows": self.trade_shows,
            "industries": [i.value for i in self.industries],
            "regions": [r.value for r in self.regions],
            "trend_category": self.trend_category,
            "strength": self.strength,
            "extracted_at": self.extracted_at,
            "cycle_id": self.cycle_id,
        }


@dataclass
class Trend:
    """A synthesized trend derived from clustered signals."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    rank: int = 0
    name: str = ""
    description: str = ""
    lifecycle: LifecycleStage = LifecycleStage.EMERGING
    composite_score: float = 0.0  # 0-100
    confidence: float = 0.0  # 0-1
    industries: list[Industry] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    cross_industry: bool = False
    scope: str = "Global"  # "Global" or specific region
    signal_ids: list[str] = field(default_factory=list)
    signal_count: int = 0
    mention_count: int = 0
    show_count: int = 0
    keywords: list[str] = field(default_factory=list)
    velocity: float = 0.0  # rate of change
    prediction: str = ""
    design_implications: str = ""
    cycle_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rank": self.rank,
            "name": self.name,
            "description": self.description,
            "lifecycle": self.lifecycle.value,
            "composite_score": self.composite_score,
            "confidence": self.confidence,
            "industries": [i.value for i in self.industries],
            "regions": [r.value for r in self.regions],
            "cross_industry": self.cross_industry,
            "scope": self.scope,
            "signal_ids": self.signal_ids,
            "signal_count": self.signal_count,
            "mention_count": self.mention_count,
            "show_count": self.show_count,
            "keywords": self.keywords,
            "velocity": self.velocity,
            "prediction": self.prediction,
            "design_implications": self.design_implications,
            "cycle_id": self.cycle_id,
        }


@dataclass
class AnalysisCycle:
    """A single run of the analysis pipeline."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    scan_type: str = "full"  # "full", "regional", "show_specific"
    scope: str = ""  # e.g., "Full Scan", "Asia-Pacific", "CES 2026"
    signal_count: int = 0
    trend_count: int = 0
    industries_covered: int = 0
    regions_covered: int = 0
    model_version: str = "v1.0"
    predictions: list[dict] = field(default_factory=list)
    eval_score: Optional[float] = None  # retrospective prediction accuracy

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "scan_type": self.scan_type,
            "scope": self.scope,
            "signal_count": self.signal_count,
            "trend_count": self.trend_count,
            "industries_covered": self.industries_covered,
            "regions_covered": self.regions_covered,
            "model_version": self.model_version,
            "predictions": self.predictions,
            "eval_score": self.eval_score,
        }


@dataclass
class Experiment:
    """An autoresearch experiment log entry (results.tsv equivalent)."""
    cycle_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    model_change: str = ""  # description of what was modified
    metric_before: float = 0.0
    metric_after: float = 0.0
    kept: bool = False  # whether the change was kept

    def to_tsv_row(self) -> str:
        return (
            f"{self.cycle_id}\t{self.timestamp}\t{self.model_change}\t"
            f"{self.metric_before:.4f}\t{self.metric_after:.4f}\t"
            f"{'kept' if self.kept else 'discarded'}"
        )
