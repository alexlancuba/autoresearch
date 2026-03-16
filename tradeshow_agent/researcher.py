"""Web research module for gathering trade show data and trends.

Uses web searches and page fetching to collect information about trade shows,
industry trends, exhibitor announcements, and market signals.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests

from .config import AgentConfig, KNOWN_TRADE_SHOWS, TRADE_SHOW_HUBS

logger = logging.getLogger(__name__)


@dataclass
class TradeShowEvent:
    """Represents a trade show or exhibition event."""
    name: str
    industry: str
    location: str
    region: str
    date_range: str = ""
    frequency: str = ""
    estimated_attendees: str = ""
    key_themes: list[str] = field(default_factory=list)
    notable_exhibitors: list[str] = field(default_factory=list)
    website: str = ""
    source: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TrendSignal:
    """A single trend signal extracted from trade show research."""
    title: str
    description: str
    industry: str
    region: str
    source_event: str
    signal_type: str  # "emerging", "growing", "mature", "declining"
    confidence: float  # 0.0 - 1.0
    keywords: list[str] = field(default_factory=list)
    related_companies: list[str] = field(default_factory=list)
    source_url: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TradeShowResearcher:
    """Gathers trade show data from web sources."""

    # Search query templates for discovering trends
    SEARCH_QUERIES = [
        "{industry} trade show {year} trends",
        "{industry} exhibition {region} {year} highlights",
        "{show_name} {year} key announcements",
        "{show_name} {year} emerging trends",
        "{industry} expo {year} innovations",
        "trade show trends {region} {year}",
        "{industry} conference {year} market outlook",
        "biggest {industry} exhibitions {year} global",
    ]

    def __init__(self, config: AgentConfig, ai_extractor=None):
        self.config = config
        self.ai_extractor = ai_extractor
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AutoResearch-TradeShowAgent/0.1 (Research Bot)"
        })
        self.events_cache_path = config.data_dir / "events_cache.json"
        self.trends_cache_path = config.data_dir / "trends_cache.json"

    def get_seed_events(self) -> list[TradeShowEvent]:
        """Return the seed list of known trade shows as TradeShowEvent objects."""
        events = []
        for show in KNOWN_TRADE_SHOWS:
            events.append(TradeShowEvent(
                name=show["name"],
                industry=show["industry"],
                location=show["location"],
                region=show["region"],
                frequency=show.get("frequency", ""),
                date_range=show.get("month", ""),
            ))
        return events

    def build_search_queries(self, industry: str = "", region: str = "",
                             show_name: str = "", year: str = "") -> list[str]:
        """Generate search queries for trade show research."""
        if not year:
            year = str(datetime.now().year)

        queries = []
        for template in self.SEARCH_QUERIES:
            try:
                query = template.format(
                    industry=industry or "technology",
                    region=region or "global",
                    show_name=show_name or "trade show",
                    year=year,
                )
                queries.append(query)
            except KeyError:
                continue
        return queries

    def search_web(self, query: str, num_results: int = 10) -> list[dict]:
        """Search the web for trade show information.

        Uses DuckDuckGo HTML search as a free, no-API-key-needed source.
        Returns a list of result dicts with 'title', 'url', 'snippet'.
        """
        results = []
        try:
            resp = self.session.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query, "kl": "wt-wt"},
                timeout=15,
            )
            resp.raise_for_status()

            # Parse results from DDG HTML response
            from html.parser import HTMLParser

            class DDGParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self.current = {}
                    self.in_title = False
                    self.in_snippet = False
                    self.capture_text = ""

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "a" and attrs_dict.get("class", "") == "result__a":
                        self.in_title = True
                        self.current = {"url": attrs_dict.get("href", ""), "title": "", "snippet": ""}
                        self.capture_text = ""
                    elif tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                        self.in_snippet = True
                        self.capture_text = ""

                def handle_endtag(self, tag):
                    if tag == "a" and self.in_title:
                        self.current["title"] = self.capture_text.strip()
                        self.in_title = False
                    elif tag == "a" and self.in_snippet:
                        self.current["snippet"] = self.capture_text.strip()
                        self.in_snippet = False
                        if self.current.get("title"):
                            self.results.append(self.current)
                        self.current = {}

                def handle_data(self, data):
                    if self.in_title or self.in_snippet:
                        self.capture_text += data

            parser = DDGParser()
            parser.feed(resp.text)
            results = parser.results[:num_results]

        except Exception as e:
            logger.warning(f"Web search failed for '{query}': {e}")

        return results

    def fetch_page_content(self, url: str, max_chars: int = 5000) -> str:
        """Fetch and extract text content from a web page."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            # Simple HTML to text extraction
            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text_parts = []
                    self.skip_tags = {"script", "style", "nav", "footer", "header"}
                    self.skip_depth = 0

                def handle_starttag(self, tag, attrs):
                    if tag in self.skip_tags:
                        self.skip_depth += 1

                def handle_endtag(self, tag):
                    if tag in self.skip_tags and self.skip_depth > 0:
                        self.skip_depth -= 1

                def handle_data(self, data):
                    if self.skip_depth == 0:
                        text = data.strip()
                        if text:
                            self.text_parts.append(text)

            extractor = TextExtractor()
            extractor.feed(resp.text)
            full_text = " ".join(extractor.text_parts)
            return full_text[:max_chars]

        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return ""

    def research_trade_show(self, show: TradeShowEvent) -> list[TrendSignal]:
        """Research a specific trade show and extract trend signals."""
        logger.info(f"Researching: {show.name} ({show.industry})")
        signals = []

        queries = self.build_search_queries(
            industry=show.industry,
            region=show.region,
            show_name=show.name,
        )

        all_content = []
        for query in queries[:3]:  # Limit to 3 queries per show
            results = self.search_web(query)
            for result in results[:3]:  # Top 3 results per query
                content = self.fetch_page_content(result["url"])
                if content:
                    all_content.append({
                        "source": result["url"],
                        "title": result["title"],
                        "snippet": result.get("snippet", ""),
                        "content": content[:2000],
                    })
            time.sleep(1)  # Rate limiting

        # Extract trends from gathered content
        # Try AI extraction first, fall back to keyword-based
        for item in all_content:
            if self.ai_extractor and self.ai_extractor.is_enabled:
                extracted = self.ai_extractor.extract_trends(
                    item["content"], show=show, source_url=item["source"],
                )
                if extracted:
                    signals.extend(extracted)
                    continue
            # Fallback: keyword-based extraction
            extracted = self._extract_trends_from_content(
                item["content"],
                show=show,
                source_url=item["source"],
            )
            signals.extend(extracted)

        return signals

    def _extract_trends_from_content(self, content: str, show: TradeShowEvent,
                                     source_url: str = "") -> list[TrendSignal]:
        """Extract trend signals from page content using keyword analysis."""
        signals = []

        # Keyword-based trend detection
        trend_indicators = {
            "AI & Machine Learning": {
                "keywords": ["artificial intelligence", "machine learning", "AI", "deep learning",
                             "generative AI", "LLM", "neural network", "computer vision"],
                "signal_type": "growing",
            },
            "Sustainability & Green Tech": {
                "keywords": ["sustainability", "green", "carbon neutral", "renewable",
                             "ESG", "circular economy", "clean energy", "net zero"],
                "signal_type": "growing",
            },
            "Digital Transformation": {
                "keywords": ["digital transformation", "digitalization", "Industry 4.0",
                             "smart factory", "IoT", "digital twin", "automation"],
                "signal_type": "mature",
            },
            "Supply Chain Innovation": {
                "keywords": ["supply chain", "logistics", "reshoring", "nearshoring",
                             "blockchain supply", "last mile", "warehouse automation"],
                "signal_type": "growing",
            },
            "Electric & Autonomous Vehicles": {
                "keywords": ["electric vehicle", "EV", "autonomous driving", "self-driving",
                             "battery technology", "charging infrastructure", "ADAS"],
                "signal_type": "growing",
            },
            "Cybersecurity": {
                "keywords": ["cybersecurity", "zero trust", "ransomware", "data privacy",
                             "threat detection", "security operations", "SIEM"],
                "signal_type": "growing",
            },
            "5G & Connectivity": {
                "keywords": ["5G", "6G", "edge computing", "network slicing",
                             "private network", "satellite internet", "connectivity"],
                "signal_type": "mature",
            },
            "Health Tech & Biotech": {
                "keywords": ["biotech", "medtech", "telemedicine", "wearable health",
                             "precision medicine", "genomics", "digital health"],
                "signal_type": "growing",
            },
            "Robotics & Automation": {
                "keywords": ["robotics", "cobot", "collaborative robot", "warehouse robot",
                             "drone", "UAV", "industrial automation", "RPA"],
                "signal_type": "growing",
            },
            "Metaverse & XR": {
                "keywords": ["metaverse", "virtual reality", "augmented reality", "XR",
                             "mixed reality", "spatial computing", "VR headset"],
                "signal_type": "emerging",
            },
            "Quantum Computing": {
                "keywords": ["quantum computing", "quantum", "qubit", "quantum advantage",
                             "quantum cryptography"],
                "signal_type": "emerging",
            },
            "Personalization & Customer Experience": {
                "keywords": ["personalization", "customer experience", "CX", "omnichannel",
                             "hyper-personalization", "retail tech"],
                "signal_type": "mature",
            },
        }

        content_lower = content.lower()
        for trend_name, info in trend_indicators.items():
            matched_keywords = [kw for kw in info["keywords"] if kw.lower() in content_lower]
            if len(matched_keywords) >= 2:  # At least 2 keyword matches
                confidence = min(len(matched_keywords) / len(info["keywords"]), 1.0)
                signals.append(TrendSignal(
                    title=trend_name,
                    description=f"Detected at {show.name}: {', '.join(matched_keywords[:3])} "
                                f"mentioned in trade show coverage from {show.region}.",
                    industry=show.industry,
                    region=show.region,
                    source_event=show.name,
                    signal_type=info["signal_type"],
                    confidence=round(confidence, 2),
                    keywords=matched_keywords,
                    source_url=source_url,
                ))

        return signals

    def research_industry(self, industry: str) -> list[TrendSignal]:
        """Research trade show trends for an entire industry."""
        logger.info(f"Researching industry: {industry}")
        signals = []

        # Find relevant shows for this industry
        relevant_shows = [s for s in self.get_seed_events() if s.industry == industry]

        # Also do general industry searches
        for region in self.config.regions:
            queries = self.build_search_queries(industry=industry, region=region)
            for query in queries[:2]:
                results = self.search_web(query)
                for result in results[:2]:
                    content = self.fetch_page_content(result["url"])
                    if content:
                        dummy_show = TradeShowEvent(
                            name=f"{industry} General",
                            industry=industry,
                            location=region,
                            region=region,
                        )
                        extracted = self._extract_trends_from_content(
                            content, show=dummy_show, source_url=result["url"]
                        )
                        signals.extend(extracted)
                time.sleep(1)

        # Research specific shows
        for show in relevant_shows:
            show_signals = self.research_trade_show(show)
            signals.extend(show_signals)

        return signals

    def research_region(self, region: str) -> list[TrendSignal]:
        """Research trade show trends for a specific global region."""
        logger.info(f"Researching region: {region}")
        signals = []

        relevant_shows = [s for s in self.get_seed_events() if s.region == region]
        for show in relevant_shows[:5]:  # Top 5 shows per region
            show_signals = self.research_trade_show(show)
            signals.extend(show_signals)

        return signals

    def save_cache(self, events: list[TradeShowEvent], signals: list[TrendSignal]):
        """Persist gathered data to cache files."""
        events_data = [
            {
                "name": e.name, "industry": e.industry, "location": e.location,
                "region": e.region, "date_range": e.date_range, "frequency": e.frequency,
                "key_themes": e.key_themes, "notable_exhibitors": e.notable_exhibitors,
                "fetched_at": e.fetched_at,
            }
            for e in events
        ]
        signals_data = [
            {
                "title": s.title, "description": s.description, "industry": s.industry,
                "region": s.region, "source_event": s.source_event,
                "signal_type": s.signal_type, "confidence": s.confidence,
                "keywords": s.keywords, "related_companies": s.related_companies,
                "source_url": s.source_url, "fetched_at": s.fetched_at,
            }
            for s in signals
        ]

        self.events_cache_path.write_text(json.dumps(events_data, indent=2))
        self.trends_cache_path.write_text(json.dumps(signals_data, indent=2))
        logger.info(f"Cached {len(events)} events and {len(signals)} trend signals")

    def load_cache(self) -> tuple[list[dict], list[dict]]:
        """Load previously cached data."""
        events = []
        signals = []
        if self.events_cache_path.exists():
            events = json.loads(self.events_cache_path.read_text())
        if self.trends_cache_path.exists():
            signals = json.loads(self.trends_cache_path.read_text())
        return events, signals
