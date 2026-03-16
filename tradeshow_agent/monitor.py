"""Health monitoring and freshness tracking for the trade show agent.

Tracks agent uptime, research cycle health, data freshness, and provides
health check endpoints for Docker/orchestration systems.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Current health status of the agent."""
    status: str = "starting"  # starting, healthy, degraded, unhealthy
    uptime_seconds: float = 0.0
    last_cycle_at: str = ""
    last_cycle_duration_seconds: float = 0.0
    last_cycle_signals: int = 0
    total_cycles: int = 0
    total_signals: int = 0
    data_freshness_minutes: float = -1.0  # -1 means no data yet
    ai_extraction_enabled: bool = False
    notifications_enabled: bool = False
    errors_last_hour: int = 0
    last_error: str = ""
    next_cycle_at: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "uptime_human": self._format_uptime(),
            "last_cycle_at": self.last_cycle_at,
            "last_cycle_duration_seconds": round(self.last_cycle_duration_seconds, 1),
            "last_cycle_signals": self.last_cycle_signals,
            "total_cycles": self.total_cycles,
            "total_signals": self.total_signals,
            "data_freshness_minutes": round(self.data_freshness_minutes, 1),
            "data_freshness_human": self._format_freshness(),
            "ai_extraction_enabled": self.ai_extraction_enabled,
            "notifications_enabled": self.notifications_enabled,
            "errors_last_hour": self.errors_last_hour,
            "last_error": self.last_error,
            "next_cycle_at": self.next_cycle_at,
        }

    def _format_uptime(self) -> str:
        s = int(self.uptime_seconds)
        if s < 60:
            return f"{s}s"
        if s < 3600:
            return f"{s // 60}m {s % 60}s"
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h}h {m}m"

    def _format_freshness(self) -> str:
        if self.data_freshness_minutes < 0:
            return "No data yet"
        m = self.data_freshness_minutes
        if m < 1:
            return "Just updated"
        if m < 60:
            return f"{int(m)}m ago"
        h = m / 60
        if h < 24:
            return f"{h:.1f}h ago"
        return f"{h / 24:.1f}d ago"


class AgentMonitor:
    """Monitors agent health, tracks metrics, and persists state."""

    def __init__(self, state_path: Path | None = None):
        self._start_time = time.time()
        self._lock = Lock()
        self._state_path = state_path or Path.home() / ".cache" / "autoresearch" / "tradeshow" / "monitor_state.json"
        self._state_path.parent.mkdir(parents=True, exist_ok=True)

        # Metrics
        self._last_cycle_at: float = 0.0
        self._last_cycle_duration: float = 0.0
        self._last_cycle_signals: int = 0
        self._total_cycles: int = 0
        self._total_signals: int = 0
        self._errors: list[tuple[float, str]] = []  # (timestamp, message)
        self._ai_enabled: bool = False
        self._notifications_enabled: bool = False
        self._next_cycle_at: float = 0.0
        self._interval_minutes: int = 30

        # Load persisted state
        self._load_state()

    def record_cycle_start(self):
        """Call when a research cycle begins."""
        with self._lock:
            self._cycle_start = time.time()

    def record_cycle_complete(self, signals_count: int):
        """Call when a research cycle completes successfully."""
        with self._lock:
            now = time.time()
            self._last_cycle_at = now
            self._last_cycle_duration = now - getattr(self, '_cycle_start', now)
            self._last_cycle_signals = signals_count
            self._total_cycles += 1
            self._total_signals += signals_count
            self._next_cycle_at = now + (self._interval_minutes * 60)
            self._save_state()

    def record_error(self, message: str):
        """Record an error event."""
        with self._lock:
            self._errors.append((time.time(), message))
            # Keep only last 100 errors
            self._errors = self._errors[-100:]
            self._save_state()

    def set_ai_enabled(self, enabled: bool):
        with self._lock:
            self._ai_enabled = enabled

    def set_notifications_enabled(self, enabled: bool):
        with self._lock:
            self._notifications_enabled = enabled

    def set_interval(self, minutes: int):
        with self._lock:
            self._interval_minutes = minutes

    def get_health(self) -> HealthStatus:
        """Get current health status."""
        with self._lock:
            now = time.time()
            uptime = now - self._start_time

            # Calculate data freshness
            if self._last_cycle_at > 0:
                freshness_min = (now - self._last_cycle_at) / 60.0
            else:
                freshness_min = -1.0

            # Count errors in last hour
            one_hour_ago = now - 3600
            recent_errors = [e for e in self._errors if e[0] > one_hour_ago]

            # Determine health status
            if self._total_cycles == 0:
                status = "starting"
            elif len(recent_errors) >= 5:
                status = "unhealthy"
            elif freshness_min > self._interval_minutes * 3:
                status = "degraded"
            elif len(recent_errors) >= 2:
                status = "degraded"
            else:
                status = "healthy"

            return HealthStatus(
                status=status,
                uptime_seconds=uptime,
                last_cycle_at=datetime.fromtimestamp(self._last_cycle_at).isoformat() if self._last_cycle_at else "",
                last_cycle_duration_seconds=self._last_cycle_duration,
                last_cycle_signals=self._last_cycle_signals,
                total_cycles=self._total_cycles,
                total_signals=self._total_signals,
                data_freshness_minutes=freshness_min,
                ai_extraction_enabled=self._ai_enabled,
                notifications_enabled=self._notifications_enabled,
                errors_last_hour=len(recent_errors),
                last_error=recent_errors[-1][1] if recent_errors else "",
                next_cycle_at=datetime.fromtimestamp(self._next_cycle_at).isoformat() if self._next_cycle_at > now else "",
            )

    def get_health_check(self) -> tuple[int, dict]:
        """Return (http_status_code, response_dict) for health check endpoint.

        Returns 200 for healthy/starting, 503 for degraded/unhealthy.
        """
        health = self.get_health()
        status_code = 200 if health.status in ("healthy", "starting") else 503
        return status_code, health.to_dict()

    def _save_state(self):
        """Persist monitoring state to disk."""
        try:
            state = {
                "total_cycles": self._total_cycles,
                "total_signals": self._total_signals,
                "last_cycle_at": self._last_cycle_at,
                "last_cycle_duration": self._last_cycle_duration,
                "last_cycle_signals": self._last_cycle_signals,
                "errors": self._errors[-20:],  # Keep last 20
                "saved_at": time.time(),
            }
            self._state_path.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save monitor state: {e}")

    def _load_state(self):
        """Load persisted monitoring state."""
        try:
            if self._state_path.exists():
                state = json.loads(self._state_path.read_text())
                self._total_cycles = state.get("total_cycles", 0)
                self._total_signals = state.get("total_signals", 0)
                self._last_cycle_at = state.get("last_cycle_at", 0.0)
                self._last_cycle_duration = state.get("last_cycle_duration", 0.0)
                self._last_cycle_signals = state.get("last_cycle_signals", 0)
                self._errors = state.get("errors", [])
                logger.info(f"Loaded monitor state: {self._total_cycles} cycles, "
                            f"{self._total_signals} signals historically")
        except Exception as e:
            logger.warning(f"Failed to load monitor state: {e}")
