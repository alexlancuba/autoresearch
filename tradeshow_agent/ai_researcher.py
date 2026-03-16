"""AI-powered trend extraction using Claude API.

Replaces simple keyword matching with Claude-powered analysis that reads
and understands articles, extracts nuanced trends, and generates
SME-quality insights for trade show exhibit designers and sales reps.
"""

import json
import logging
import os
from dataclasses import dataclass

from .researcher import TrendSignal, TradeShowEvent

logger = logging.getLogger(__name__)


# Claude API prompt for deep trend extraction
TREND_EXTRACTION_SYSTEM = """You are an expert trade show industry analyst providing intelligence
to exhibit designers and sales reps who need to position themselves as subject matter experts
on global trends in design, engagement, technology, and market dynamics across all industries.

Your analysis should help them:
- Advise clients and prospects on the latest trends relevant to their industry
- Identify competitive advantages through emerging innovations
- Understand regional market differences and opportunities
- Spot cross-industry convergence themes they can leverage in exhibit designs

Be specific, actionable, and forward-looking. Avoid generic observations."""

TREND_EXTRACTION_PROMPT = """Analyze this trade show / industry content and extract trend signals.

**Context:**
- Trade Show/Event: {event_name}
- Industry: {industry}
- Region: {region}
- Source: {source_url}

**Content to analyze:**
{content}

**Extract trends as a JSON array. For each trend provide:**
{{
  "title": "Short, specific trend name (not generic like 'AI' — be specific, e.g. 'AI-Powered Exhibit Personalization')",
  "description": "2-3 sentence explanation written for a trade show exhibit designer or sales rep. What does this mean for their clients? How should they position around it?",
  "signal_type": "emerging | growing | mature | declining",
  "confidence": 0.0 to 1.0,
  "keywords": ["specific", "relevant", "keywords"],
  "related_companies": ["companies mentioned or associated"],
  "exhibit_implications": "One sentence on what this means for exhibit design or sales positioning",
  "client_talking_point": "One sentence a sales rep could say to a prospect to demonstrate expertise"
}}

Return ONLY a JSON array. If no meaningful trends found, return [].
Extract 1-5 trends maximum. Quality over quantity."""


@dataclass
class AIResearchConfig:
    """Configuration for AI-powered research."""
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2000
    enabled: bool = False

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.enabled = bool(self.api_key)


class AITrendExtractor:
    """Uses Claude API to extract nuanced trend signals from web content.

    Falls back to keyword-based extraction if API is not configured.
    """

    def __init__(self, config: AIResearchConfig | None = None):
        self.config = config or AIResearchConfig()
        self._client = None

        if self.config.enabled:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.api_key)
                logger.info("AI trend extraction enabled (Claude API)")
            except ImportError:
                logger.warning("anthropic package not installed. "
                               "Install with: pip install anthropic")
                self.config.enabled = False
            except Exception as e:
                logger.warning(f"Failed to initialize Claude client: {e}")
                self.config.enabled = False
        else:
            logger.info("AI trend extraction disabled (no ANTHROPIC_API_KEY). "
                        "Using keyword-based extraction.")

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled and self._client is not None

    def extract_trends(self, content: str, show: TradeShowEvent,
                       source_url: str = "") -> list[TrendSignal]:
        """Extract trends using Claude AI analysis.

        Args:
            content: Web page text content to analyze.
            show: The trade show event context.
            source_url: URL of the source content.

        Returns:
            List of TrendSignal objects with AI-extracted insights.
        """
        if not self.is_enabled:
            return []

        if not content or len(content.strip()) < 100:
            return []

        prompt = TREND_EXTRACTION_PROMPT.format(
            event_name=show.name,
            industry=show.industry,
            region=show.region,
            source_url=source_url or "unknown",
            content=content[:4000],  # Limit content size
        )

        try:
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=TREND_EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse the response
            response_text = response.content[0].text.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first and last lines (``` markers)
                lines = [l for l in lines if not l.strip().startswith("```")]
                response_text = "\n".join(lines)

            trends_data = json.loads(response_text)

            if not isinstance(trends_data, list):
                logger.warning("AI response was not a JSON array")
                return []

            signals = []
            for trend in trends_data:
                if not isinstance(trend, dict) or "title" not in trend:
                    continue

                signal = TrendSignal(
                    title=trend.get("title", "Unknown Trend"),
                    description=self._build_description(trend, show),
                    industry=show.industry,
                    region=show.region,
                    source_event=show.name,
                    signal_type=trend.get("signal_type", "growing"),
                    confidence=min(max(float(trend.get("confidence", 0.5)), 0.0), 1.0),
                    keywords=trend.get("keywords", [])[:10],
                    related_companies=trend.get("related_companies", [])[:5],
                    source_url=source_url,
                )
                signals.append(signal)

            logger.info(f"AI extracted {len(signals)} trends from {show.name} content")
            return signals

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return []
        except Exception as e:
            logger.warning(f"AI trend extraction failed: {e}")
            return []

    def _build_description(self, trend: dict, show: TradeShowEvent) -> str:
        """Build a rich description from AI-extracted trend data."""
        parts = [trend.get("description", "")]

        exhibit_imp = trend.get("exhibit_implications", "")
        if exhibit_imp:
            parts.append(f"Exhibit impact: {exhibit_imp}")

        talking_point = trend.get("client_talking_point", "")
        if talking_point:
            parts.append(f"Rep talking point: \"{talking_point}\"")

        return " | ".join(p for p in parts if p)

    def generate_sme_briefing(self, signals: list[TrendSignal],
                               industry: str = "",
                               region: str = "") -> str:
        """Generate an SME briefing document from accumulated signals.

        This creates the kind of document a sales rep can read before
        a client meeting to sound like an industry expert.
        """
        if not self.is_enabled:
            return ""

        # Build context from signals
        signal_summaries = []
        for s in signals[:20]:  # Top 20 signals
            signal_summaries.append(
                f"- {s.title} ({s.signal_type}, confidence: {s.confidence}): "
                f"{s.description[:200]}"
            )

        context_filter = ""
        if industry:
            context_filter += f"\nFocus industry: {industry}"
        if region:
            context_filter += f"\nFocus region: {region}"

        prompt = f"""Based on these trade show trend signals, write a concise SME briefing
for a trade show exhibit sales rep who needs to sound like an industry expert
in their next client meeting.
{context_filter}

**Trend Signals:**
{chr(10).join(signal_summaries)}

**Write the briefing in this format:**

## Quick Industry Pulse (3-4 bullet points)
What's hot right now? What are prospects hearing about?

## Key Trends to Reference in Conversations
For each trend (top 5): what it is, why it matters to the client, and a
specific thing the rep can say to demonstrate expertise.

## Competitive Intelligence
What are leading exhibitors doing differently? What can our clients learn?

## Conversation Starters
3-4 specific questions a rep can ask a prospect that demonstrate deep
industry knowledge.

Keep it punchy and practical. No fluff. A sales rep should be able to
read this in 3 minutes and walk into a meeting sounding like they live
and breathe this industry."""

        try:
            response = self._client.messages.create(
                model=self.config.model,
                max_tokens=3000,
                system=TREND_EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Failed to generate SME briefing: {e}")
            return ""
