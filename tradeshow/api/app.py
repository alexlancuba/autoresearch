"""
Trade Show Trend Analysis API — Back of House.

Production-grade REST API serving the agentic intelligence layer.
This is the ONLY interface between the backend agents and any frontend
(Lovable, custom React, mobile app, etc.).

- OpenAPI docs at /docs
- All endpoints versioned under /api/v1/
- Backward-compatible /api/ redirects to /api/v1/
- CORS configured via CORS_ORIGINS env var
- Auth-ready middleware (no-op for MVP)
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── Configuration ────────────────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
API_VERSION = "v1"
APP_VERSION = "1.0.0"

_start_time = time.time()

# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Trade Show Trend Analysis API",
    description=(
        "REST API for the Trade Show Trend Intelligence platform. "
        "Serves trend data, signals, trade shows, media assets, and analysis controls. "
        "Designed for consumption by any frontend (Lovable, React, mobile)."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth-ready middleware (no-op for MVP) ────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Auth-ready middleware. Currently passes all requests through.

    When you're ready to add authentication, validate the token here.
    Change ONE function — not every endpoint.
    """
    auth_header = request.headers.get("Authorization", "")
    request.state.auth_token = auth_header
    # TODO: Add auth validation here (API key, JWT, OAuth)
    response = await call_next(request)
    return response


# ── Pydantic Response Models ─────────────────────────────────────────────────


class TrendResponse(BaseModel):
    id: str = ""
    rank: int = 0
    name: str = ""
    description: str = ""
    lifecycle: str = ""
    composite_score: float = 0.0
    confidence: float = 0.0
    industries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    cross_industry: bool = False
    scope: str = ""
    signal_ids: list[str] = Field(default_factory=list)
    signal_count: int = 0
    mention_count: int = 0
    show_count: int = 0
    keywords: list[str] = Field(default_factory=list)
    velocity: float = 0.0
    prediction: str = ""
    design_implications: str = ""
    cycle_id: str = ""
    media_ids: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class SignalResponse(BaseModel):
    id: str = ""
    text: str = ""
    source_url: str = ""
    source_type: str = ""
    trade_shows: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    trend_category: str = ""
    strength: float = 0.0
    extracted_at: str = ""
    cycle_id: str = ""
    media_ids: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class TradeShowResponse(BaseModel):
    id: str = ""
    name: str = ""
    short_name: str = ""
    industries: list[str] = Field(default_factory=list)
    region: str = ""
    city: str = ""
    country: str = ""
    frequency: str = ""
    tier: str = ""
    typical_exhibitors: int = 0
    typical_attendees: int = 0
    next_date: Optional[str] = None
    website: str = ""
    media_ids: list[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class CycleResponse(BaseModel):
    id: str = ""
    timestamp: str = ""
    scan_type: str = ""
    scope: str = ""
    signal_count: int = 0
    trend_count: int = 0
    industries_covered: int = 0
    regions_covered: int = 0
    model_version: str = ""
    predictions: list[dict] = Field(default_factory=list)
    eval_score: Optional[float] = None

    class Config:
        extra = "allow"


class MediaAssetResponse(BaseModel):
    id: str = ""
    url: str = ""
    thumbnail_url: str = ""
    media_type: str = ""
    source: str = ""
    source_url: str = ""
    caption: str = ""
    trade_shows: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    trend_categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    width: int = 0
    height: int = 0
    fetched_at: str = ""
    cycle_id: str = ""

    class Config:
        extra = "allow"


class StatsResponse(BaseModel):
    total_signals: int = 0
    total_trends: int = 0
    total_shows: int = 0
    total_cycles: int = 0
    total_media: int = 0
    industries_count: int = 0
    regions_count: int = 0


class HealthResponse(BaseModel):
    status: str
    version: str
    api_version: str
    timestamp: str
    data_counts: dict[str, int]
    scraper_status: dict[str, Any]
    uptime_seconds: int


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status_code: int


# ── Paginated list wrappers ──────────────────────────────────────────────────

class TrendListResponse(BaseModel):
    trends: list[TrendResponse]
    count: int
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None


class SignalListResponse(BaseModel):
    signals: list[SignalResponse]
    count: int
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None


class ShowListResponse(BaseModel):
    shows: list[TradeShowResponse]
    count: int
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None


class CycleListResponse(BaseModel):
    cycles: list[CycleResponse]
    count: int


class MediaListResponse(BaseModel):
    media: list[MediaAssetResponse]
    count: int
    page: Optional[int] = None
    page_size: Optional[int] = None
    total: Optional[int] = None


class IndustryListResponse(BaseModel):
    industries: list[str]


class RegionListResponse(BaseModel):
    regions: list[str]


# ── Request models ───────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    scope: Optional[str] = "Full Scan"
    industry: Optional[str] = None
    region: Optional[str] = None
    show: Optional[str] = None


class ScrapeRequest(BaseModel):
    offline: bool = True
    max_results: int = 50
    scope: str = "Full Scan"


class AnalyzeResponse(BaseModel):
    cycle: CycleResponse
    trends: list[TrendResponse]
    signal_count: int


class ScrapeResponse(BaseModel):
    status: str
    result: Optional[dict] = None
    message: Optional[str] = None


class ScrapeStatusResponse(BaseModel):
    running: bool
    last_result: Optional[dict] = None


# ── Error handlers ───────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Not Found" if exc.status_code == 404 else "Error",
            "detail": str(exc.detail),
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "status_code": 500,
        },
    )


# ── In-memory data store ────────────────────────────────────────────────────

_data: dict[str, list[dict]] = {
    "trends": [],
    "signals": [],
    "shows": [],
    "cycles": [],
    "media": [],
}

_scrape_status: dict = {"running": False, "last_result": None}


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
    _data["media"] = _load_json("media.json")


@app.on_event("startup")
def startup_load_data() -> None:
    _reload_data()


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _paginate(items: list, page: Optional[int], page_size: Optional[int]) -> tuple[list, Optional[int], Optional[int], Optional[int]]:
    """Apply optional pagination. Returns (items, page, page_size, total)."""
    if page is None or page_size is None:
        return items, None, None, None
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], page, page_size, total


# ══════════════════════════════════════════════════════════════════════════════
# VERSIONED ENDPOINTS — /api/v1/
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
def health_check_v1():
    """Check API health, version, data counts, and scraper status."""
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        api_version=API_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        data_counts={k: len(v) for k, v in _data.items()},
        scraper_status={
            "running": _scrape_status["running"],
            "last_run": (_scrape_status["last_result"] or {}).get("timestamp"),
        },
        uptime_seconds=int(time.time() - _start_time),
    )


# ── Trends ───────────────────────────────────────────────────────────────────

@app.get("/api/v1/trends", response_model=TrendListResponse, tags=["Trends"])
def list_trends_v1(
    industry: Optional[str] = Query(None, description="Filter by industry name"),
    region: Optional[str] = Query(None, description="Filter by region name"),
    cycle_id: Optional[str] = Query(None, description="Filter by analysis cycle ID"),
    page: Optional[int] = Query(None, ge=1, description="Page number (omit for all)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
):
    """List all trends, optionally filtered by industry, region, or cycle."""
    results = _data["trends"]
    if industry:
        results = [t for t in results if _matches(t, "industries", industry)]
    if region:
        results = [t for t in results if _matches(t, "regions", region)]
    if cycle_id:
        results = [t for t in results if t.get("cycle_id") == cycle_id]
    items, pg, ps, total = _paginate(results, page, page_size)
    return TrendListResponse(trends=items, count=len(items), page=pg, page_size=ps, total=total)


@app.get("/api/v1/trends/{trend_id}", response_model=TrendResponse, tags=["Trends"])
def get_trend_v1(trend_id: str):
    """Get a single trend by ID."""
    for trend in _data["trends"]:
        if trend.get("id") == trend_id:
            return trend
    raise HTTPException(status_code=404, detail=f"Trend '{trend_id}' not found")


@app.get("/api/v1/trends/{trend_id}/media", response_model=MediaListResponse, tags=["Trends"])
def get_trend_media_v1(trend_id: str):
    """Get media assets associated with a trend."""
    trend = None
    for t in _data["trends"]:
        if t.get("id") == trend_id:
            trend = t
            break
    if not trend:
        raise HTTPException(status_code=404, detail=f"Trend '{trend_id}' not found")
    media_ids = set(trend.get("media_ids", []))
    trend_name = trend.get("name", "")
    results = [
        m for m in _data["media"]
        if m.get("id") in media_ids or trend_name in m.get("trend_categories", [])
    ]
    return MediaListResponse(media=results, count=len(results))


# ── Signals ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/signals", response_model=SignalListResponse, tags=["Signals"])
def list_signals_v1(
    industry: Optional[str] = Query(None, description="Filter by industry name"),
    region: Optional[str] = Query(None, description="Filter by region name"),
    trend_category: Optional[str] = Query(None, description="Filter by trend category"),
    cycle_id: Optional[str] = Query(None, description="Filter by analysis cycle ID"),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
):
    """List all signals, optionally filtered."""
    results = _data["signals"]
    if industry:
        results = [s for s in results if _matches(s, "industries", industry)]
    if region:
        results = [s for s in results if _matches(s, "regions", region)]
    if trend_category:
        results = [s for s in results if s.get("trend_category") == trend_category]
    if cycle_id:
        results = [s for s in results if s.get("cycle_id") == cycle_id]
    items, pg, ps, total = _paginate(results, page, page_size)
    return SignalListResponse(signals=items, count=len(items), page=pg, page_size=ps, total=total)


# ── Trade Shows ──────────────────────────────────────────────────────────────

@app.get("/api/v1/shows", response_model=ShowListResponse, tags=["Trade Shows"])
def list_shows_v1(
    industry: Optional[str] = Query(None, description="Filter by industry name"),
    region: Optional[str] = Query(None, description="Filter by region name"),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
):
    """List all trade shows, optionally filtered."""
    results = _data["shows"]
    if industry:
        results = [s for s in results if _matches(s, "industries", industry)]
    if region:
        results = [s for s in results if _matches(s, "region", region)]
    items, pg, ps, total = _paginate(results, page, page_size)
    return ShowListResponse(shows=items, count=len(items), page=pg, page_size=ps, total=total)


@app.get("/api/v1/shows/{show_id}/media", response_model=MediaListResponse, tags=["Trade Shows"])
def get_show_media_v1(show_id: str):
    """Get media assets associated with a trade show."""
    show = None
    for s in _data["shows"]:
        if s.get("id") == show_id:
            show = s
            break
    if not show:
        raise HTTPException(status_code=404, detail=f"Show '{show_id}' not found")
    short_name = show.get("short_name", "")
    results = [m for m in _data["media"] if short_name in m.get("trade_shows", [])]
    return MediaListResponse(media=results, count=len(results))


# ── Cycles ───────────────────────────────────────────────────────────────────

@app.get("/api/v1/cycles", response_model=CycleListResponse, tags=["Analysis"])
def list_cycles_v1():
    """List all analysis cycles (run history)."""
    return CycleListResponse(cycles=_data["cycles"], count=len(_data["cycles"]))


# ── Metadata ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/industries", response_model=IndustryListResponse, tags=["Metadata"])
def list_industries_v1():
    """List all unique industries across trends, signals, and shows."""
    industries: set[str] = set()
    for key in ("trends", "signals", "shows"):
        industries.update(_extract_unique(_data[key], "industries"))
    return IndustryListResponse(industries=sorted(industries))


@app.get("/api/v1/regions", response_model=RegionListResponse, tags=["Metadata"])
def list_regions_v1():
    """List all unique regions across trends, signals, and shows."""
    regions: set[str] = set()
    for key in ("trends", "signals"):
        regions.update(_extract_unique(_data[key], "regions"))
    regions.update(_extract_unique(_data["shows"], "region"))
    return RegionListResponse(regions=sorted(regions))


@app.get("/api/v1/stats", response_model=StatsResponse, tags=["Metadata"])
def get_stats_v1():
    """Get aggregate statistics for the dashboard overview."""
    industries: set[str] = set()
    regions: set[str] = set()
    for key in ("trends", "signals", "shows"):
        industries.update(_extract_unique(_data[key], "industries"))
    for key in ("trends", "signals"):
        regions.update(_extract_unique(_data[key], "regions"))
    regions.update(_extract_unique(_data["shows"], "region"))
    return StatsResponse(
        total_signals=len(_data["signals"]),
        total_trends=len(_data["trends"]),
        total_shows=len(_data["shows"]),
        total_cycles=len(_data["cycles"]),
        total_media=len(_data["media"]),
        industries_count=len(industries),
        regions_count=len(regions),
    )


# ── Media ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/media", response_model=MediaListResponse, tags=["Media"])
def list_media_v1(
    trade_show: Optional[str] = Query(None, description="Filter by trade show short name"),
    trend_category: Optional[str] = Query(None, description="Filter by trend category"),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=200),
):
    """List media assets (photos, videos, thumbnails) with optional filters."""
    results = _data["media"]
    if trade_show:
        results = [m for m in results if trade_show in m.get("trade_shows", [])]
    if trend_category:
        results = [m for m in results if trend_category in m.get("trend_categories", [])]
    if media_type:
        results = [m for m in results if m.get("media_type") == media_type]
    items, pg, ps, total = _paginate(results, page, page_size)
    return MediaListResponse(media=items, count=len(items), page=pg, page_size=ps, total=total)


# ── Analysis & Scraping ──────────────────────────────────────────────────────

@app.post("/api/v1/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
def run_analysis_v1(request: AnalyzeRequest):
    """Run an analysis cycle: filter signals and return current trends."""
    _reload_data()
    signals = _data["signals"]
    if request.industry:
        signals = [s for s in signals if _matches(s, "industries", request.industry)]
    if request.region:
        signals = [s for s in signals if _matches(s, "regions", request.region)]
    if request.show:
        signals = [s for s in signals if request.show in s.get("trade_shows", [])]
    trends = _data["trends"]
    if request.industry:
        trends = [t for t in trends if _matches(t, "industries", request.industry)]
    if request.region:
        trends = [t for t in trends if _matches(t, "regions", request.region)]
    cycle = CycleResponse(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        scan_type="full" if not (request.industry or request.region or request.show) else "filtered",
        scope=request.scope or "Full Scan",
        signal_count=len(signals),
        trend_count=len(trends),
        industries_covered=len(_extract_unique(signals, "industries")),
        regions_covered=len(_extract_unique(signals, "regions")),
        model_version="v1.0",
    )
    return AnalyzeResponse(cycle=cycle, trends=trends, signal_count=len(signals))


@app.post("/api/v1/scrape", response_model=ScrapeResponse, tags=["Scraping"])
async def trigger_scrape_v1(request: ScrapeRequest):
    """Trigger a data collection cycle (RSS, YouTube, web scraping)."""
    if _scrape_status["running"]:
        return ScrapeResponse(status="already_running", message="A scrape is already in progress")
    _scrape_status["running"] = True
    try:
        from tradeshow.scrapers.pipeline import run_pipeline
        result = await run_pipeline(
            offline=request.offline,
            max_results=request.max_results,
            scope=request.scope,
        )
        _scrape_status["last_result"] = result
        _reload_data()
        return ScrapeResponse(status="complete", result=result)
    except Exception as e:
        return ScrapeResponse(status="error", message=str(e))
    finally:
        _scrape_status["running"] = False


@app.get("/api/v1/scrape/status", response_model=ScrapeStatusResponse, tags=["Scraping"])
def scrape_status_v1():
    """Check the status of the last/current scrape operation."""
    return ScrapeStatusResponse(
        running=_scrape_status["running"],
        last_result=_scrape_status["last_result"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# BACKWARD-COMPATIBLE ROUTES — /api/ redirects to /api/v1/
# These keep the existing dashboard working without changes.
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health", include_in_schema=False)
def health_check():
    return health_check_v1()

@app.get("/api/trends", include_in_schema=False)
def list_trends(industry: Optional[str] = Query(None), region: Optional[str] = Query(None), cycle_id: Optional[str] = Query(None)):
    return list_trends_v1(industry=industry, region=region, cycle_id=cycle_id)

@app.get("/api/trends/{trend_id}", include_in_schema=False)
def get_trend(trend_id: str):
    return get_trend_v1(trend_id)

@app.get("/api/trends/{trend_id}/media", include_in_schema=False)
def get_trend_media(trend_id: str):
    return get_trend_media_v1(trend_id)

@app.get("/api/signals", include_in_schema=False)
def list_signals(industry: Optional[str] = Query(None), region: Optional[str] = Query(None), trend_category: Optional[str] = Query(None), cycle_id: Optional[str] = Query(None)):
    return list_signals_v1(industry=industry, region=region, trend_category=trend_category, cycle_id=cycle_id)

@app.get("/api/shows", include_in_schema=False)
def list_shows(industry: Optional[str] = Query(None), region: Optional[str] = Query(None)):
    return list_shows_v1(industry=industry, region=region)

@app.get("/api/shows/{show_id}/media", include_in_schema=False)
def get_show_media(show_id: str):
    return get_show_media_v1(show_id)

@app.get("/api/cycles", include_in_schema=False)
def list_cycles():
    return list_cycles_v1()

@app.get("/api/industries", include_in_schema=False)
def list_industries():
    return list_industries_v1()

@app.get("/api/regions", include_in_schema=False)
def list_regions():
    return list_regions_v1()

@app.get("/api/stats", include_in_schema=False)
def get_stats():
    return get_stats_v1()

@app.get("/api/media", include_in_schema=False)
def list_media(trade_show: Optional[str] = Query(None), trend_category: Optional[str] = Query(None), media_type: Optional[str] = Query(None)):
    return list_media_v1(trade_show=trade_show, trend_category=trend_category, media_type=media_type)

@app.post("/api/analyze", include_in_schema=False)
def run_analysis(request: AnalyzeRequest):
    return run_analysis_v1(request)

@app.post("/api/scrape", include_in_schema=False)
async def trigger_scrape(request: ScrapeRequest):
    return await trigger_scrape_v1(request)

@app.get("/api/scrape/status", include_in_schema=False)
def scrape_status():
    return scrape_status_v1()
