"""
LLM-powered signal extraction from raw articles.

Takes RawArticle objects and uses an LLM to extract structured Signal
dicts with trend_category, industries, regions, and strength scores.
Uses the extraction prompt templates defined in the SignalCollector config.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

from .base import RawArticle

logger = logging.getLogger(__name__)

# The system prompt that guides the LLM's signal extraction
SYSTEM_PROMPT = """You are a trade show trend analysis agent. You extract structured signals
from articles about trade shows, exhibitions, and industry events.

For each article, extract zero or more trend signals. Each signal should identify:
1. trend_category: One of these categories:
   - AI & Machine Learning
   - Sustainability & Green Tech
   - Robotics & Automation
   - Electric & Autonomous Vehicles
   - Cybersecurity
   - Digital Transformation
   - Health Tech & Biotech
   - Supply Chain Innovation
   - Quantum Computing
   - Spatial Computing & XR

2. industries: List of relevant industries from:
   Technology & Electronics, Healthcare & Medical Devices, Automotive & Transportation,
   Food & Beverage, Energy & Sustainability, Fashion & Textiles, Construction & Real Estate,
   Agriculture & Farming, Defense & Aerospace, Retail & E-Commerce, Manufacturing & Industrial,
   Telecommunications, Entertainment & Media, Logistics & Supply Chain, Finance & Fintech

3. regions: List of relevant regions from:
   North America, Europe, Asia-Pacific, Middle East & Africa, Latin America

4. trade_shows: List of trade show names mentioned (e.g., "CES", "Hannover Messe", "MEDICA")

5. strength: A float from 0.0 to 1.0 indicating signal strength:
   - 0.9-1.0: Major announcement, quantitative data, official report
   - 0.7-0.9: Significant coverage, multiple sources, analyst opinion
   - 0.5-0.7: Notable mention, single source, anecdotal
   - 0.3-0.5: Weak signal, passing mention

6. text: A 1-2 sentence summary of the specific signal

Respond with a JSON array of signal objects. If no trade show signals are present, return [].
"""


class SignalExtractor:
    """Extracts structured signals from raw articles using an LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        taxonomy: Optional[list[str]] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.taxonomy = taxonomy or [
            "AI & Machine Learning",
            "Sustainability & Green Tech",
            "Robotics & Automation",
            "Electric & Autonomous Vehicles",
            "Cybersecurity",
            "Digital Transformation",
            "Health Tech & Biotech",
            "Supply Chain Innovation",
            "Quantum Computing",
            "Spatial Computing & XR",
        ]
        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package required for LLM extraction. "
                    "Install with: pip install anthropic"
                )
        return self._client

    def extract_signals(
        self,
        articles: list[RawArticle],
        cycle_id: str = "",
    ) -> list[dict]:
        """Extract structured signals from a batch of articles.

        Args:
            articles: Raw articles to process.
            cycle_id: Current analysis cycle ID.

        Returns:
            List of Signal dicts ready for the pipeline.
        """
        all_signals: list[dict] = []

        for article in articles:
            if not article.text and not article.title:
                continue

            try:
                signals = self._extract_from_article(article, cycle_id)
                all_signals.extend(signals)
                logger.info(
                    f"Extracted {len(signals)} signals from: {article.title[:60]}"
                )
            except Exception as e:
                logger.warning(f"Extraction failed for {article.url}: {e}")

        return all_signals

    def _extract_from_article(
        self, article: RawArticle, cycle_id: str
    ) -> list[dict]:
        """Extract signals from a single article via LLM."""
        # Build the user prompt
        user_prompt = f"""Analyze this trade show article and extract trend signals.

Title: {article.title}
Source: {article.source_name}
Published: {article.published_at or 'Unknown'}

Content:
{article.text[:3000]}

Extract all trade show trend signals as a JSON array."""

        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse the LLM response
        response_text = response.content[0].text
        signals_data = self._parse_json_response(response_text)

        # Convert to Signal dicts
        signals = []
        for i, sig_data in enumerate(signals_data):
            trend_cat = sig_data.get("trend_category", "")
            if trend_cat not in self.taxonomy:
                continue  # Skip signals outside our taxonomy

            signal = {
                "id": f"live-{article.content_hash}-{i:02d}",
                "text": sig_data.get("text", article.title),
                "source_url": article.url,
                "source_type": article.source_type,
                "trade_shows": sig_data.get("trade_shows", article.trade_show_mentions),
                "industries": sig_data.get("industries", []),
                "regions": sig_data.get("regions", []),
                "trend_category": trend_cat,
                "strength": min(max(float(sig_data.get("strength", 0.5)), 0.0), 1.0),
                "extracted_at": datetime.utcnow().isoformat(),
                "cycle_id": cycle_id,
                "media_ids": [],
            }

            # Attach article images as potential media references
            if article.images:
                signal["_source_images"] = article.images[:5]

            signals.append(signal)

        return signals

    def extract_signals_offline(
        self,
        articles: list[RawArticle],
        cycle_id: str = "",
    ) -> list[dict]:
        """Extract signals without LLM — uses keyword matching.

        Fallback when no API key is configured. Less accurate but works
        without any external dependencies.
        """
        all_signals: list[dict] = []

        # Keyword → trend category mapping
        keyword_map = {
            "AI & Machine Learning": [
                "artificial intelligence", "machine learning", "generative ai",
                "llm", "large language model", "ai copilot", "chatgpt", "deep learning",
                "neural network", "ai chip", "edge ai",
            ],
            "Sustainability & Green Tech": [
                "sustainability", "green tech", "renewable energy", "solar",
                "wind energy", "hydrogen", "carbon neutral", "net zero",
                "circular economy", "sustainable packaging",
            ],
            "Robotics & Automation": [
                "robot", "cobot", "automation", "humanoid", "amr",
                "autonomous mobile", "warehouse automation", "surgical robot",
            ],
            "Electric & Autonomous Vehicles": [
                "electric vehicle", "ev", "autonomous driving", "self-driving",
                "solid-state battery", "ev charging", "800v",
            ],
            "Cybersecurity": [
                "cybersecurity", "zero trust", "ransomware", "threat detection",
                "quantum-safe", "encryption", "data breach",
            ],
            "Digital Transformation": [
                "digital twin", "industry 4.0", "iot", "smart factory",
                "digital transformation", "smart store", "proptech",
            ],
            "Health Tech & Biotech": [
                "medtech", "biotech", "wearable health", "precision medicine",
                "telemedicine", "point-of-care", "diagnostics", "mRNA",
            ],
            "Supply Chain Innovation": [
                "supply chain", "nearshoring", "logistics", "fulfillment",
                "demand forecasting", "cold chain", "food traceability",
            ],
            "Quantum Computing": [
                "quantum computing", "qubit", "quantum-safe", "quantum advantage",
                "quantum as a service",
            ],
            "Spatial Computing & XR": [
                "spatial computing", "augmented reality", "virtual reality",
                "mixed reality", "xr", "metaverse", "vision pro",
            ],
        }

        for article in articles:
            combined = f"{article.title} {article.text}".lower()

            for category, keywords in keyword_map.items():
                matches = [kw for kw in keywords if kw in combined]
                if len(matches) >= 2:  # Require at least 2 keyword matches
                    strength = min(0.4 + 0.1 * len(matches), 0.85)
                    signal = {
                        "id": f"offline-{article.content_hash}-{category[:3].lower()}",
                        "text": f"{article.title}. Keywords: {', '.join(matches[:3])}",
                        "source_url": article.url,
                        "source_type": article.source_type,
                        "trade_shows": article.trade_show_mentions,
                        "industries": [],  # Would need mapping
                        "regions": [],
                        "trend_category": category,
                        "strength": strength,
                        "extracted_at": datetime.utcnow().isoformat(),
                        "cycle_id": cycle_id,
                        "media_ids": [],
                    }
                    if article.images:
                        signal["_source_images"] = article.images[:5]
                    all_signals.append(signal)

        return all_signals

    @staticmethod
    def _parse_json_response(text: str) -> list[dict]:
        """Parse JSON array from LLM response text."""
        # Try direct parse
        text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        import re
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Try finding array brackets
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                result = json.loads(text[start:end + 1])
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse LLM response as JSON array")
        return []
