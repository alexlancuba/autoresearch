"""Main Trade Show Trend Analysis Agent.

Autonomous agent that continuously researches trade shows across industries
and global regions, analyzes trends, and generates periodic insight reports.

Follows the autoresearch pattern: an autonomous loop that runs indefinitely,
gathering data, analyzing trends, and producing actionable reports.
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from .analyzer import TrendAnalyzer
from .config import AgentConfig, INDUSTRIES, REGIONS
from .reports import ReportGenerator, print_report_summary
from .researcher import TradeShowResearcher, TrendSignal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tradeshow_agent.log"),
    ],
)
logger = logging.getLogger(__name__)


class TradeShowAgent:
    """Autonomous trade show trend analysis agent.

    The agent runs in a continuous loop:
    1. Research trade shows across configured industries and regions
    2. Extract trend signals from web sources
    3. Analyze and aggregate trends
    4. Generate reports with insights
    5. Sleep, then repeat
    """

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.researcher = TradeShowResearcher(self.config)
        self.analyzer = TrendAnalyzer(top_n=self.config.top_trends_count)
        self.reporter = ReportGenerator(self.config.reports_dir)
        self.cycle_count = 0
        self.all_signals: list[TrendSignal] = []

    def run_once(self, industries: list[str] | None = None,
                 regions: list[str] | None = None,
                 output_format: str = "markdown") -> Path:
        """Run a single research-analyze-report cycle.

        Args:
            industries: Industries to research (default: all configured).
            regions: Regions to research (default: all configured).
            output_format: Report format - "markdown", "json", or "html".

        Returns:
            Path to the generated report file.
        """
        self.cycle_count += 1
        cycle_start = time.time()
        logger.info(f"=== Starting research cycle {self.cycle_count} ===")

        target_industries = industries or self.config.industries
        target_regions = regions or self.config.regions

        # Phase 1: Research
        cycle_signals = []

        logger.info(f"Phase 1: Researching {len(target_industries)} industries "
                     f"across {len(target_regions)} regions")

        # Research by industry
        for industry in target_industries:
            try:
                signals = self.researcher.research_industry(industry)
                cycle_signals.extend(signals)
                logger.info(f"  {industry}: {len(signals)} signals")
            except Exception as e:
                logger.error(f"  {industry}: research failed - {e}")

        # Research by region (catches shows not industry-filtered)
        for region in target_regions:
            try:
                signals = self.researcher.research_region(region)
                cycle_signals.extend(signals)
                logger.info(f"  {region}: {len(signals)} signals")
            except Exception as e:
                logger.error(f"  {region}: research failed - {e}")

        # Deduplicate signals
        cycle_signals = self._deduplicate_signals(cycle_signals)
        self.all_signals.extend(cycle_signals)
        logger.info(f"Phase 1 complete: {len(cycle_signals)} unique signals this cycle, "
                     f"{len(self.all_signals)} total accumulated")

        # Phase 2: Analyze
        logger.info("Phase 2: Analyzing trends")
        report = self.analyzer.analyze(self.all_signals)

        # Phase 3: Generate report
        logger.info(f"Phase 3: Generating {output_format} report")
        report_path = self.reporter.generate(report, fmt=output_format)

        # Print summary
        print_report_summary(report)

        # Cache data
        events = self.researcher.get_seed_events()
        self.researcher.save_cache(events, self.all_signals)

        elapsed = time.time() - cycle_start
        logger.info(f"=== Cycle {self.cycle_count} complete in {elapsed:.1f}s ===")
        logger.info(f"Report saved: {report_path}")

        return report_path

    def run_continuous(self, interval_minutes: int | None = None,
                       output_format: str = "markdown"):
        """Run the agent in continuous mode, looping forever.

        Follows the autoresearch pattern: LOOP FOREVER, never stopping
        until manually interrupted.

        Args:
            interval_minutes: Minutes between cycles (default: from config).
            output_format: Report format for each cycle.
        """
        interval = interval_minutes or self.config.research_interval_minutes
        logger.info(f"Starting continuous mode (interval: {interval} min)")
        logger.info(f"Industries: {len(self.config.industries)}")
        logger.info(f"Regions: {len(self.config.regions)}")
        logger.info("Press Ctrl+C to stop.")

        while True:
            try:
                report_path = self.run_once(output_format=output_format)
                logger.info(f"Next cycle in {interval} minutes...")
                time.sleep(interval * 60)
            except KeyboardInterrupt:
                logger.info("Agent stopped by user.")
                break
            except Exception as e:
                logger.error(f"Cycle failed: {e}", exc_info=True)
                logger.info(f"Retrying in {interval} minutes...")
                time.sleep(interval * 60)

    def run_focused(self, industry: str | None = None,
                    region: str | None = None,
                    show_name: str | None = None,
                    output_format: str = "markdown") -> Path:
        """Run a focused analysis on a specific industry, region, or show.

        Args:
            industry: Specific industry to analyze.
            region: Specific region to analyze.
            show_name: Specific trade show to research.
            output_format: Report format.

        Returns:
            Path to the generated report.
        """
        signals = []

        if show_name:
            # Find the show in seed data
            matching = [
                s for s in self.researcher.get_seed_events()
                if show_name.lower() in s.name.lower()
            ]
            if matching:
                for show in matching:
                    show_signals = self.researcher.research_trade_show(show)
                    signals.extend(show_signals)
            else:
                logger.warning(f"Show '{show_name}' not found in seed data. "
                               "Doing general search.")
                from .researcher import TradeShowEvent
                generic = TradeShowEvent(
                    name=show_name,
                    industry=industry or "General",
                    location="Global",
                    region=region or "Global",
                )
                signals = self.researcher.research_trade_show(generic)

        if industry:
            ind_signals = self.researcher.research_industry(industry)
            signals.extend(ind_signals)

        if region:
            reg_signals = self.researcher.research_region(region)
            signals.extend(reg_signals)

        signals = self._deduplicate_signals(signals)
        self.all_signals.extend(signals)

        report = self.analyzer.analyze(signals)
        report_path = self.reporter.generate(report, fmt=output_format)
        print_report_summary(report)

        return report_path

    def _deduplicate_signals(self, signals: list[TrendSignal]) -> list[TrendSignal]:
        """Remove duplicate signals based on title + event + region."""
        seen = set()
        unique = []
        for s in signals:
            key = (s.title, s.source_event, s.region)
            if key not in seen:
                seen.add(key)
                unique.append(s)
        return unique

    def get_status(self) -> dict:
        """Return the agent's current status."""
        return {
            "cycles_completed": self.cycle_count,
            "total_signals": len(self.all_signals),
            "industries_tracked": len(self.config.industries),
            "regions_tracked": len(self.config.regions),
            "seed_events": len(self.researcher.get_seed_events()),
        }


def main():
    """CLI entry point for the trade show agent."""
    parser = argparse.ArgumentParser(
        description="Trade Show Trend Analysis AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single analysis cycle across all industries/regions
  python -m tradeshow_agent.agent

  # Run continuous monitoring (every 30 minutes)
  python -m tradeshow_agent.agent --continuous

  # Focus on a specific industry
  python -m tradeshow_agent.agent --industry "Technology & Electronics"

  # Focus on a specific region
  python -m tradeshow_agent.agent --region "Asia-Pacific"

  # Research a specific trade show
  python -m tradeshow_agent.agent --show "CES"

  # Generate HTML report
  python -m tradeshow_agent.agent --format html

  # Custom interval for continuous mode
  python -m tradeshow_agent.agent --continuous --interval 60
        """,
    )

    parser.add_argument("--continuous", action="store_true",
                        help="Run in continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=30,
                        help="Minutes between research cycles (default: 30)")
    parser.add_argument("--industry", type=str,
                        help="Focus on a specific industry")
    parser.add_argument("--region", type=str,
                        help="Focus on a specific global region")
    parser.add_argument("--show", type=str,
                        help="Research a specific trade show")
    parser.add_argument("--format", type=str, default="markdown",
                        choices=["markdown", "json", "html"],
                        help="Output report format (default: markdown)")
    parser.add_argument("--reports-dir", type=str, default="tradeshow_reports",
                        help="Directory for output reports")
    parser.add_argument("--list-industries", action="store_true",
                        help="List all tracked industries")
    parser.add_argument("--list-regions", action="store_true",
                        help="List all tracked regions")
    parser.add_argument("--list-shows", action="store_true",
                        help="List all known trade shows")

    args = parser.parse_args()

    # Info commands
    if args.list_industries:
        print("Tracked Industries:")
        for ind in INDUSTRIES:
            print(f"  - {ind}")
        return

    if args.list_regions:
        print("Tracked Regions:")
        for reg in REGIONS:
            print(f"  - {reg}")
        return

    if args.list_shows:
        from .config import KNOWN_TRADE_SHOWS
        print(f"Known Trade Shows ({len(KNOWN_TRADE_SHOWS)}):")
        for show in KNOWN_TRADE_SHOWS:
            print(f"  - {show['name']} ({show['industry']}) - "
                  f"{show['location']}, {show.get('month', 'TBD')}")
        return

    # Configure and run
    config = AgentConfig(reports_dir=Path(args.reports_dir))
    agent = TradeShowAgent(config=config)

    if args.show or args.industry or args.region:
        # Focused analysis
        agent.run_focused(
            industry=args.industry,
            region=args.region,
            show_name=args.show,
            output_format=args.format,
        )
    elif args.continuous:
        # Continuous mode
        agent.run_continuous(
            interval_minutes=args.interval,
            output_format=args.format,
        )
    else:
        # Single cycle
        agent.run_once(output_format=args.format)


if __name__ == "__main__":
    main()
