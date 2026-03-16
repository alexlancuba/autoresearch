"""Web server for the Trade Show Trend Analysis dashboard.

A lightweight HTTP server using only Python's standard library.
Serves the dashboard UI and provides JSON API endpoints for the agent.
Includes health check endpoint for Docker/orchestration health monitoring.
"""

import json
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .config import AgentConfig, INDUSTRIES, REGIONS, KNOWN_TRADE_SHOWS

logger = logging.getLogger(__name__)

# Global agent instance and state
_agent = None
_running = False
_last_report: dict | None = None
_run_history: list[dict] = []
_background_thread: threading.Thread | None = None


def get_agent():
    global _agent
    if _agent is None:
        from .agent import TradeShowAgent
        _agent = TradeShowAgent(config=AgentConfig())
    return _agent


def set_agent(agent):
    """Set the global agent instance (used when starting server with existing agent)."""
    global _agent
    _agent = agent


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    def log_message(self, format, *args):
        logger.debug(format % args)

    def _send_json(self, data: dict | list, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/" or path == "/dashboard":
            self._serve_dashboard()
        elif path == "/api/status":
            self._api_status()
        elif path == "/api/health":
            self._api_health()
        elif path == "/api/industries":
            self._send_json(INDUSTRIES)
        elif path == "/api/regions":
            self._send_json(REGIONS)
        elif path == "/api/shows":
            self._send_json(KNOWN_TRADE_SHOWS)
        elif path == "/api/report":
            self._api_report()
        elif path == "/api/history":
            self._send_json(_run_history)
        elif path == "/api/signals":
            self._api_signals()
        elif path == "/api/briefing":
            self._api_briefing(params)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        if path == "/api/run":
            self._api_run(data)
        elif path == "/api/stop":
            self._api_stop()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_dashboard(self):
        html_path = Path(__file__).parent / "dashboard.html"
        if html_path.exists():
            self._send_html(html_path.read_text())
        else:
            self._send_html("<h1>Dashboard file not found</h1>", 500)

    def _api_status(self):
        agent = get_agent()
        status = agent.get_status()
        status["is_running"] = _running
        status["has_report"] = _last_report is not None
        status["run_count"] = len(_run_history)
        self._send_json(status)

    def _api_health(self):
        """Health check endpoint for Docker/orchestration."""
        agent = get_agent()
        status_code, health_data = agent.monitor.get_health_check()
        self._send_json(health_data, status=status_code)

    def _api_report(self):
        if _last_report is not None:
            self._send_json(_last_report)
        else:
            self._send_json({"error": "No report available. Run an analysis first."}, 404)

    def _api_signals(self):
        agent = get_agent()
        signals = []
        for s in agent.all_signals:
            signals.append({
                "title": s.title,
                "description": s.description,
                "industry": s.industry,
                "region": s.region,
                "source_event": s.source_event,
                "signal_type": s.signal_type,
                "confidence": s.confidence,
                "keywords": s.keywords,
                "fetched_at": s.fetched_at,
            })
        self._send_json(signals)

    def _api_briefing(self, params: dict):
        """Generate an SME briefing for sales reps."""
        agent = get_agent()
        industry = params.get("industry", [""])[0]
        region = params.get("region", [""])[0]

        briefing = agent.generate_sme_briefing(industry=industry, region=region)
        if briefing:
            self._send_json({"briefing": briefing, "industry": industry, "region": region})
        else:
            self._send_json({
                "error": "AI extraction not enabled or no signals available. "
                         "Set ANTHROPIC_API_KEY and run an analysis first.",
                "briefing": "",
            }, 404)

    def _api_run(self, data: dict):
        global _running, _background_thread

        if _running:
            self._send_json({"error": "Analysis is already running"}, 409)
            return

        industry = data.get("industry")
        region = data.get("region")
        show = data.get("show")
        fmt = data.get("format", "json")

        _running = True
        _background_thread = threading.Thread(
            target=_run_analysis,
            args=(industry, region, show, fmt),
            daemon=True,
        )
        _background_thread.start()

        self._send_json({"status": "started", "industry": industry,
                         "region": region, "show": show})

    def _api_stop(self):
        global _running
        _running = False
        self._send_json({"status": "stopped"})


def _run_analysis(industry: str | None, region: str | None,
                  show: str | None, fmt: str):
    """Run analysis in a background thread."""
    global _running, _last_report

    agent = get_agent()
    start = time.time()

    try:
        if show or industry or region:
            report_path = agent.run_focused(
                industry=industry, region=region,
                show_name=show, output_format="json",
            )
        else:
            report_path = agent.run_once(output_format="json")

        # Load the JSON report for the API
        if report_path.exists() and report_path.suffix == ".json":
            _last_report = json.loads(report_path.read_text())
        else:
            # Generate a JSON version too
            from .analyzer import TrendAnalyzer
            analyzer = TrendAnalyzer()
            report = analyzer.analyze(agent.all_signals)
            from .reports import ReportGenerator
            gen = ReportGenerator(agent.config.reports_dir)
            json_path = gen.generate(report, fmt="json")
            _last_report = json.loads(json_path.read_text())

        elapsed = round(time.time() - start, 1)
        _run_history.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "industry": industry,
            "region": region,
            "show": show,
            "signals": len(agent.all_signals),
            "elapsed_seconds": elapsed,
            "status": "completed",
        })

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        _run_history.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "industry": industry,
            "region": region,
            "show": show,
            "signals": 0,
            "elapsed_seconds": round(time.time() - start, 1),
            "status": f"error: {e}",
        })
    finally:
        _running = False


def run_server(host: str = "0.0.0.0", port: int = 8050):
    """Start the dashboard web server (blocking)."""
    server = HTTPServer((host, port), DashboardHandler)
    print(f"\n{'=' * 60}")
    print(f"  Trade Show Trend Analysis Dashboard")
    print(f"  Running at: http://localhost:{port}")
    print(f"  Health check: http://localhost:{port}/api/health")
    print(f"{'=' * 60}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


def run_server_background(host: str = "0.0.0.0", port: int = 8050, agent=None):
    """Start the dashboard web server in a background thread.

    Used when running --continuous --ui together.
    """
    if agent is not None:
        set_agent(agent)

    server = HTTPServer((host, port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Dashboard server started in background at http://localhost:{port}")
    logger.info(f"Health check: http://localhost:{port}/api/health")
