"""Configuration for the Trade Show Trend Analysis Agent."""

from dataclasses import dataclass, field
from pathlib import Path


# --- Industry Categories ---
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

# --- Global Regions ---
REGIONS = [
    "North America",
    "Europe",
    "Asia-Pacific",
    "Middle East & Africa",
    "Latin America",
]

# --- Major Trade Show Hubs ---
TRADE_SHOW_HUBS = {
    "North America": [
        "Las Vegas, USA",
        "Chicago, USA",
        "New York, USA",
        "Orlando, USA",
        "Toronto, Canada",
        "San Francisco, USA",
    ],
    "Europe": [
        "Hannover, Germany",
        "Frankfurt, Germany",
        "Barcelona, Spain",
        "Paris, France",
        "Milan, Italy",
        "London, UK",
        "Amsterdam, Netherlands",
    ],
    "Asia-Pacific": [
        "Shanghai, China",
        "Shenzhen, China",
        "Tokyo, Japan",
        "Seoul, South Korea",
        "Singapore",
        "Sydney, Australia",
        "Mumbai, India",
    ],
    "Middle East & Africa": [
        "Dubai, UAE",
        "Riyadh, Saudi Arabia",
        "Cape Town, South Africa",
        "Abu Dhabi, UAE",
    ],
    "Latin America": [
        "Sao Paulo, Brazil",
        "Mexico City, Mexico",
        "Buenos Aires, Argentina",
        "Bogota, Colombia",
    ],
}

# --- Well-Known Trade Shows (seed data) ---
KNOWN_TRADE_SHOWS = [
    {"name": "CES", "industry": "Technology & Electronics", "location": "Las Vegas, USA", "region": "North America", "frequency": "Annual", "month": "January"},
    {"name": "MWC (Mobile World Congress)", "industry": "Telecommunications", "location": "Barcelona, Spain", "region": "Europe", "frequency": "Annual", "month": "February"},
    {"name": "Hannover Messe", "industry": "Manufacturing & Industrial", "location": "Hannover, Germany", "region": "Europe", "frequency": "Annual", "month": "April"},
    {"name": "MEDICA", "industry": "Healthcare & Medical Devices", "location": "Dusseldorf, Germany", "region": "Europe", "frequency": "Annual", "month": "November"},
    {"name": "SXSW", "industry": "Technology & Electronics", "location": "Austin, USA", "region": "North America", "frequency": "Annual", "month": "March"},
    {"name": "NRF (National Retail Federation)", "industry": "Retail & E-Commerce", "location": "New York, USA", "region": "North America", "frequency": "Annual", "month": "January"},
    {"name": "Computex", "industry": "Technology & Electronics", "location": "Taipei, Taiwan", "region": "Asia-Pacific", "frequency": "Annual", "month": "June"},
    {"name": "GITEX", "industry": "Technology & Electronics", "location": "Dubai, UAE", "region": "Middle East & Africa", "frequency": "Annual", "month": "October"},
    {"name": "Canton Fair", "industry": "Manufacturing & Industrial", "location": "Guangzhou, China", "region": "Asia-Pacific", "frequency": "Biannual", "month": "April/October"},
    {"name": "Auto Shanghai / Auto China", "industry": "Automotive & Transportation", "location": "Shanghai/Beijing, China", "region": "Asia-Pacific", "frequency": "Biannual", "month": "April"},
    {"name": "SIAL Paris", "industry": "Food & Beverage", "location": "Paris, France", "region": "Europe", "frequency": "Biennial", "month": "October"},
    {"name": "Intersolar", "industry": "Energy & Sustainability", "location": "Munich, Germany", "region": "Europe", "frequency": "Annual", "month": "June"},
    {"name": "SHOT Show", "industry": "Defense & Aerospace", "location": "Las Vegas, USA", "region": "North America", "frequency": "Annual", "month": "January"},
    {"name": "Bauma", "industry": "Construction & Real Estate", "location": "Munich, Germany", "region": "Europe", "frequency": "Triennial", "month": "April"},
    {"name": "Agritechnica", "industry": "Agriculture & Farming", "location": "Hannover, Germany", "region": "Europe", "frequency": "Biennial", "month": "November"},
    {"name": "IFA Berlin", "industry": "Technology & Electronics", "location": "Berlin, Germany", "region": "Europe", "frequency": "Annual", "month": "September"},
    {"name": "Web Summit", "industry": "Technology & Electronics", "location": "Lisbon, Portugal", "region": "Europe", "frequency": "Annual", "month": "November"},
    {"name": "ChinaJoy", "industry": "Entertainment & Media", "location": "Shanghai, China", "region": "Asia-Pacific", "frequency": "Annual", "month": "July"},
    {"name": "LogiMAT", "industry": "Logistics & Supply Chain", "location": "Stuttgart, Germany", "region": "Europe", "frequency": "Annual", "month": "March"},
    {"name": "Money20/20", "industry": "Finance & Fintech", "location": "Las Vegas, USA", "region": "North America", "frequency": "Annual", "month": "October"},
    {"name": "FITUR", "industry": "Retail & E-Commerce", "location": "Madrid, Spain", "region": "Europe", "frequency": "Annual", "month": "January"},
    {"name": "Gulfood", "industry": "Food & Beverage", "location": "Dubai, UAE", "region": "Middle East & Africa", "frequency": "Annual", "month": "February"},
    {"name": "Tokyo Game Show", "industry": "Entertainment & Media", "location": "Tokyo, Japan", "region": "Asia-Pacific", "frequency": "Annual", "month": "September"},
    {"name": "FIME", "industry": "Healthcare & Medical Devices", "location": "Miami, USA", "region": "North America", "frequency": "Annual", "month": "June"},
    {"name": "ADIPEC", "industry": "Energy & Sustainability", "location": "Abu Dhabi, UAE", "region": "Middle East & Africa", "frequency": "Annual", "month": "November"},
    {"name": "Texworld Paris", "industry": "Fashion & Textiles", "location": "Paris, France", "region": "Europe", "frequency": "Biannual", "month": "February/September"},
    {"name": "ExpoAlimentaria", "industry": "Food & Beverage", "location": "Lima, Peru", "region": "Latin America", "frequency": "Annual", "month": "September"},
    {"name": "AAPEX", "industry": "Automotive & Transportation", "location": "Las Vegas, USA", "region": "North America", "frequency": "Annual", "month": "November"},
]


@dataclass
class AgentConfig:
    """Configuration for the trade show analysis agent."""

    # Data storage
    data_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "autoresearch" / "tradeshow")
    reports_dir: Path = field(default_factory=lambda: Path("tradeshow_reports"))

    # Research parameters
    industries: list[str] = field(default_factory=lambda: INDUSTRIES.copy())
    regions: list[str] = field(default_factory=lambda: REGIONS.copy())

    # Analysis cycle
    research_interval_minutes: int = 30
    max_concurrent_searches: int = 5

    # Report settings
    top_trends_count: int = 10
    include_sentiment: bool = True
    output_format: str = "markdown"  # markdown, json, or html

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
