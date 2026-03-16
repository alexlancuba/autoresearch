/**
 * Trade Show Trend Analysis — Reference API Client
 *
 * Copy this into your Lovable project and set API_BASE_URL
 * to your deployed backend URL.
 *
 * Example:
 *   const API_BASE_URL = "https://tradeshow-api.up.railway.app";
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_VERSION = "v1";
const BASE = `${API_BASE_URL}/api/${API_VERSION}`;

async function fetchJSON<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), {
    headers: {
      "Content-Type": "application/json",
      // Auth-ready: uncomment when backend enables auth
      // "Authorization": `Bearer ${getToken()}`,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ── Types (match OpenAPI spec) ──────────────────────────────────────────────

export interface Trend {
  id: string;
  rank: number;
  name: string;
  description: string;
  lifecycle: "emerging" | "growing" | "mature" | "declining";
  composite_score: number;
  confidence: number;
  industries: string[];
  regions: string[];
  cross_industry: boolean;
  scope: string;
  signal_ids: string[];
  signal_count: number;
  mention_count: number;
  show_count: number;
  keywords: string[];
  velocity: number;
  prediction: string;
  design_implications: string;
  cycle_id: string;
  media_ids: string[];
}

export interface Signal {
  id: string;
  text: string;
  source_url: string;
  source_type: string;
  trade_shows: string[];
  industries: string[];
  regions: string[];
  trend_category: string;
  strength: number;
  extracted_at: string;
  cycle_id: string;
  media_ids: string[];
}

export interface TradeShow {
  id: string;
  name: string;
  short_name: string;
  industries: string[];
  region: string;
  city: string;
  country: string;
  frequency: string;
  tier: string;
  typical_exhibitors: number;
  typical_attendees: number;
  next_date: string | null;
  website: string;
  media_ids: string[];
}

export interface AnalysisCycle {
  id: string;
  timestamp: string;
  scan_type: string;
  scope: string;
  signal_count: number;
  trend_count: number;
  industries_covered: number;
  regions_covered: number;
  model_version: string;
}

export interface MediaAsset {
  id: string;
  url: string;
  thumbnail_url: string;
  media_type: "photo" | "video" | "thumbnail" | "floor_plan" | "render";
  source: string;
  source_url: string;
  caption: string;
  trade_shows: string[];
  industries: string[];
  trend_categories: string[];
  tags: string[];
  width: number;
  height: number;
  fetched_at: string;
  cycle_id: string;
}

export interface Stats {
  total_signals: number;
  total_trends: number;
  total_shows: number;
  total_cycles: number;
  total_media: number;
  industries_count: number;
  regions_count: number;
}

export interface Health {
  status: string;
  version: string;
  api_version: string;
  timestamp: string;
  data_counts: Record<string, number>;
  scraper_status: { running: boolean; last_run: string | null };
  uptime_seconds: number;
}

// ── API Methods ─────────────────────────────────────────────────────────────

export const api = {
  // Health
  getHealth: () => fetchJSON<Health>("/health"),

  // Trends
  getTrends: (industry?: string, region?: string, page?: number, pageSize?: number) =>
    fetchJSON<{ trends: Trend[]; count: number; page?: number; page_size?: number; total?: number }>(
      "/trends",
      {
        industry: industry || "",
        region: region || "",
        ...(page ? { page: String(page) } : {}),
        ...(pageSize ? { page_size: String(pageSize) } : {}),
      }
    ),

  getTrend: (id: string) => fetchJSON<Trend>(`/trends/${id}`),

  getTrendMedia: (id: string) =>
    fetchJSON<{ media: MediaAsset[]; count: number }>(`/trends/${id}/media`),

  // Signals
  getSignals: (filters?: { industry?: string; region?: string; trend_category?: string; page?: number; page_size?: number }) =>
    fetchJSON<{ signals: Signal[]; count: number; page?: number; page_size?: number; total?: number }>(
      "/signals",
      Object.fromEntries(
        Object.entries(filters || {}).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])
      )
    ),

  // Shows
  getShows: (industry?: string, region?: string) =>
    fetchJSON<{ shows: TradeShow[]; count: number }>(
      "/shows",
      { industry: industry || "", region: region || "" }
    ),

  getShowMedia: (id: string) =>
    fetchJSON<{ media: MediaAsset[]; count: number }>(`/shows/${id}/media`),

  // Cycles
  getCycles: () => fetchJSON<{ cycles: AnalysisCycle[]; count: number }>("/cycles"),

  // Metadata
  getIndustries: () => fetchJSON<{ industries: string[] }>("/industries"),
  getRegions: () => fetchJSON<{ regions: string[] }>("/regions"),
  getStats: () => fetchJSON<Stats>("/stats"),

  // Media
  getMedia: (filters?: { trade_show?: string; trend_category?: string; media_type?: string; page?: number; page_size?: number }) =>
    fetchJSON<{ media: MediaAsset[]; count: number; page?: number; page_size?: number; total?: number }>(
      "/media",
      Object.fromEntries(
        Object.entries(filters || {}).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])
      )
    ),

  // Analysis
  runAnalysis: (scope: string, industry?: string, region?: string, show?: string) =>
    fetch(`${BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, industry, region, show }),
    }).then((r) => r.json()),

  // Scraping
  triggerScrape: (offline = true, maxResults = 50) =>
    fetch(`${BASE}/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offline, max_results: maxResults }),
    }).then((r) => r.json()),

  getScrapeStatus: () =>
    fetchJSON<{ running: boolean; last_result: unknown }>("/scrape/status"),
};
