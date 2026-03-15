# Trade Show Trend Analysis Agent

An autonomous AI agent that researches, analyzes, and reports on trade show trends across industries and global markets.

## Overview

This agent follows the autoresearch experiment loop pattern, adapted for trade show intelligence:

1. **Research** — Gather data from web sources about trade shows, exhibitions, and industry conferences worldwide
2. **Extract** — Identify trend signals from trade show coverage, announcements, and exhibitor highlights
3. **Analyze** — Aggregate trends, score significance, identify cross-industry themes and regional patterns
4. **Report** — Generate actionable insight reports in Markdown, JSON, or HTML
5. **Loop** — Repeat on a configurable interval for continuous market monitoring

## Capabilities

### Industry Coverage (15 Industries)
- Technology & Electronics
- Healthcare & Medical Devices
- Automotive & Transportation
- Food & Beverage
- Energy & Sustainability
- Fashion & Textiles
- Construction & Real Estate
- Agriculture & Farming
- Defense & Aerospace
- Retail & E-Commerce
- Manufacturing & Industrial
- Telecommunications
- Entertainment & Media
- Logistics & Supply Chain
- Finance & Fintech

### Global Regions
- North America (Las Vegas, Chicago, New York, Orlando, Toronto, San Francisco)
- Europe (Hannover, Frankfurt, Barcelona, Paris, Milan, London, Amsterdam)
- Asia-Pacific (Shanghai, Shenzhen, Tokyo, Seoul, Singapore, Sydney, Mumbai)
- Middle East & Africa (Dubai, Riyadh, Cape Town, Abu Dhabi)
- Latin America (Sao Paulo, Mexico City, Buenos Aires, Bogota)

### Seed Data
28+ major global trade shows pre-loaded as research starting points, including CES, MWC, Hannover Messe, MEDICA, Canton Fair, GITEX, and more.

## Usage

```bash
# Single analysis cycle (all industries, all regions)
uv run python -m tradeshow_agent

# Continuous monitoring (every 30 minutes)
uv run python -m tradeshow_agent --continuous

# Focus on a specific industry
uv run python -m tradeshow_agent --industry "Technology & Electronics"

# Focus on a specific region
uv run python -m tradeshow_agent --region "Asia-Pacific"

# Research a specific trade show
uv run python -m tradeshow_agent --show "CES"

# Generate HTML report
uv run python -m tradeshow_agent --format html

# Custom interval for continuous mode
uv run python -m tradeshow_agent --continuous --interval 60

# List tracked industries, regions, or shows
uv run python -m tradeshow_agent --list-industries
uv run python -m tradeshow_agent --list-regions
uv run python -m tradeshow_agent --list-shows
```

## Architecture

```
tradeshow_agent/
├── __init__.py        # Package init
├── __main__.py        # CLI entry: python -m tradeshow_agent
├── agent.py           # Main agent with autonomous loop
├── config.py          # Industries, regions, trade show seed data
├── researcher.py      # Web research & trend signal extraction
├── analyzer.py        # Trend aggregation, scoring, insights
└── reports.py         # Report generation (Markdown/JSON/HTML)
```

### Data Flow

```
Web Sources → Researcher → TrendSignals → Analyzer → AnalysisReport → Reporter → Files
                  ↑                                                         ↓
                  └──────────── Cache (events + signals) ←──────────────────┘
```

### Trend Detection

The agent uses keyword-based trend detection across 12 trend categories:
- AI & Machine Learning
- Sustainability & Green Tech
- Digital Transformation
- Supply Chain Innovation
- Electric & Autonomous Vehicles
- Cybersecurity
- 5G & Connectivity
- Health Tech & Biotech
- Robotics & Automation
- Metaverse & XR
- Quantum Computing
- Personalization & Customer Experience

### Scoring Model

Trends are scored on a composite basis:
- **Frequency** — More mentions across sources = higher score
- **Confidence** — Average keyword match density
- **Cross-Industry Reach** — Trends spanning 3+ industries get a bonus
- **Global Spread** — Trends found in 3+ regions get a bonus
- **Signal Type** — Emerging trends score higher than mature ones
- **Source Diversity** — More distinct trade shows = higher reliability

## Output

Reports include:
- **Global Top Trends** — Ranked by composite score
- **Cross-Industry Themes** — Trends that span multiple sectors
- **Industry Insights** — Per-industry trend direction, key themes, active shows
- **Regional Insights** — Per-region market sentiment, dominant industries
- **Emerging Opportunities** — Actionable signals for strategic planning

## The Autonomous Loop

Like the core autoresearch agent, this agent is designed to run indefinitely in `--continuous` mode. Each cycle:

1. Searches the web for current trade show coverage
2. Extracts trend signals via keyword analysis
3. Accumulates signals across cycles (building richer data over time)
4. Produces updated reports with the latest insights
5. Caches all data for persistence

The agent builds up a richer picture over time — each cycle adds new signals to the accumulated dataset, making trend detection more accurate and comprehensive with each pass.
