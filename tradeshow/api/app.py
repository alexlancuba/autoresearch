"""FastAPI application for the Trade Show Trend Analysis dashboard."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Data directory ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Trade Show Trend Analysis API",
    description="API for the Trade Show Trend Analysis dashboard.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory data store ─────────────────────────────────────────────────────

_data: dict[str, list[dict]] = {
    "trends": [],
    "signals": [],
    "shows": [],
    "cycles": [],
}


def _load_json(filename: str) -> list[dict]:
    """Load a JSON file from the data directory, returning [] on any error."""
    path = DATA_DIR / filename
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _reload_data() -> None:
    """(Re)load all data files."""
    _data["trends"] = _load_json("trends.json")
    _data["signals"] = _load_json("signals.json")
    _data["shows"] = _load_json("shows.json")
    _data["cycles"] = _load_json("cycles.json")


@app.on_event("startup")
def startup_load_data() -> None:
    _reload_data()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_unique(items: list[dict], key: str) -> list[str]:
    """Collect unique string values (or list-of-string values) for *key*."""
    values: set[str] = set()
    for item in items:
        val = item.get(key)
        if isinstance(val, list):
            values.update(str(v) for v in val)
        elif val is not None:
            values.add(str(val))
    return sorted(values)


def _matches(item: dict, key: str, value: str) -> bool:
    """Check if an item's field matches *value* (works for str or list)."""
    field = item.get(key)
    if field is None:
        return False
    if isinstance(field, list):
        return value in field
    return str(field) == value


# ── Request models ────────────────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    scope: Optional[str] = "Full Scan"
    industry: Optional[str] = None
    region: Optional[str] = None
    show: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(DATA_DIR),
        "counts": {k: len(v) for k, v in _data.items()},
    }


@app.get("/api/trends")
def list_trends(
    industry: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    cycle_id: Optional[str] = Query(None),
):
    results = _data["trends"]
    if industry:
        results = [t for t in results if _matches(t, "industries", industry)]
    if region:
        results = [t for t in results if _matches(t, "regions", region)]
    if cycle_id:
        results = [t for t in results if t.get("cycle_id") == cycle_id]
    return {"trends": results, "count": len(results)}


@app.get("/api/trends/{trend_id}")
def get_trend(trend_id: str):
    for trend in _data["trends"]:
        if trend.get("id") == trend_id:
            return trend
    raise HTTPException(status_code=404, detail=f"Trend '{trend_id}' not found")


@app.get("/api/signals")
def list_signals(
    industry: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    trend_category: Optional[str] = Query(None),
    cycle_id: Optional[str] = Query(None),
):
    results = _data["signals"]
    if industry:
        results = [s for s in results if _matches(s, "industries", industry)]
    if region:
        results = [s for s in results if _matches(s, "regions", region)]
    if trend_category:
        results = [s for s in results if s.get("trend_category") == trend_category]
    if cycle_id:
        results = [s for s in results if s.get("cycle_id") == cycle_id]
    return {"signals": results, "count": len(results)}


@app.get("/api/shows")
def list_shows(
    industry: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    results = _data["shows"]
    if industry:
        results = [s for s in results if _matches(s, "industries", industry)]
    if region:
        results = [s for s in results if _matches(s, "region", region)]
    return {"shows": results, "count": len(results)}


@app.get("/api/cycles")
def list_cycles():
    return {"cycles": _data["cycles"], "count": len(_data["cycles"])}


@app.get("/api/industries")
def list_industries():
    industries: set[str] = set()
    for key in ("trends", "signals", "shows"):
        industries.update(_extract_unique(_data[key], "industries"))
    return {"industries": sorted(industries)}


@app.get("/api/regions")
def list_regions():
    regions: set[str] = set()
    for key in ("trends", "signals"):
        regions.update(_extract_unique(_data[key], "regions"))
    # Shows use singular "region"
    regions.update(_extract_unique(_data["shows"], "region"))
    return {"regions": sorted(regions)}


@app.get("/api/stats")
def get_stats():
    industries = set[str]()
    regions = set[str]()
    for key in ("trends", "signals", "shows"):
        industries.update(_extract_unique(_data[key], "industries"))
    for key in ("trends", "signals"):
        regions.update(_extract_unique(_data[key], "regions"))
    regions.update(_extract_unique(_data["shows"], "region"))

    return {
        "total_signals": len(_data["signals"]),
        "total_trends": len(_data["trends"]),
        "total_shows": len(_data["shows"]),
        "total_cycles": len(_data["cycles"]),
        "industries_count": len(industries),
        "regions_count": len(regions),
    }


@app.post("/api/analyze")
def run_analysis(request: AnalyzeRequest):
    """Simulate an analysis cycle: filter signals, return current trends."""
    # Reload data to pick up any new files
    _reload_data()

    # Filter signals based on request
    signals = _data["signals"]
    if request.industry:
        signals = [s for s in signals if _matches(s, "industries", request.industry)]
    if request.region:
        signals = [s for s in signals if _matches(s, "regions", request.region)]
    if request.show:
        signals = [
            s for s in signals
            if request.show in s.get("trade_shows", [])
        ]

    # Filter trends the same way
    trends = _data["trends"]
    if request.industry:
        trends = [t for t in trends if _matches(t, "industries", request.industry)]
    if request.region:
        trends = [t for t in trends if _matches(t, "regions", request.region)]

    # Build a simulated cycle record
    cycle_id = str(uuid.uuid4())[:8]
    cycle = {
        "id": cycle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_type": "full" if not (request.industry or request.region or request.show) else "filtered",
        "scope": request.scope or "Full Scan",
        "signal_count": len(signals),
        "trend_count": len(trends),
        "industries_covered": len(_extract_unique(signals, "industries")),
        "regions_covered": len(_extract_unique(signals, "regions")),
        "model_version": "v1.0",
        "predictions": [],
        "eval_score": None,
    }

    return {
        "cycle": cycle,
        "trends": trends,
        "signal_count": len(signals),
    }
