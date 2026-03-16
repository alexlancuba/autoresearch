import type { Trend, Signal, TradeShow, AnalysisCycle, Stats, MediaAsset } from "./types";

const API_BASE = "/api";

async function fetchJSON<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getTrends: async (industry?: string, region?: string): Promise<Trend[]> => {
    const data = await fetchJSON<{ trends: Trend[]; count: number }>(
      `${API_BASE}/trends`,
      { industry: industry || "", region: region || "" }
    );
    return data.trends;
  },

  getSignals: async (industry?: string, region?: string): Promise<Signal[]> => {
    const data = await fetchJSON<{ signals: Signal[]; count: number }>(
      `${API_BASE}/signals`,
      { industry: industry || "", region: region || "" }
    );
    return data.signals;
  },

  getShows: async (industry?: string, region?: string): Promise<TradeShow[]> => {
    const data = await fetchJSON<{ shows: TradeShow[]; count: number }>(
      `${API_BASE}/shows`,
      { industry: industry || "", region: region || "" }
    );
    return data.shows;
  },

  getCycles: async (): Promise<AnalysisCycle[]> => {
    const data = await fetchJSON<{ cycles: AnalysisCycle[]; count: number }>(
      `${API_BASE}/cycles`
    );
    return data.cycles;
  },

  getIndustries: async (): Promise<string[]> => {
    const data = await fetchJSON<{ industries: string[] }>(`${API_BASE}/industries`);
    return data.industries;
  },

  getRegions: async (): Promise<string[]> => {
    const data = await fetchJSON<{ regions: string[] }>(`${API_BASE}/regions`);
    return data.regions;
  },

  getStats: async (): Promise<Stats> => {
    const data = await fetchJSON<Record<string, number>>(`${API_BASE}/stats`);
    return {
      total_signals: data.total_signals ?? 0,
      total_cycles: data.total_cycles ?? 0,
      total_industries: data.industries_count ?? 0,
      total_regions: data.regions_count ?? 0,
    };
  },

  getMedia: async (tradeShow?: string, trendCategory?: string): Promise<MediaAsset[]> => {
    const data = await fetchJSON<{ media: MediaAsset[]; count: number }>(
      `${API_BASE}/media`,
      { trade_show: tradeShow || "", trend_category: trendCategory || "" }
    );
    return data.media;
  },

  getTrendMedia: async (trendId: string): Promise<MediaAsset[]> => {
    const data = await fetchJSON<{ media: MediaAsset[]; count: number }>(
      `${API_BASE}/trends/${trendId}/media`
    );
    return data.media;
  },

  getShowMedia: async (showId: string): Promise<MediaAsset[]> => {
    const data = await fetchJSON<{ media: MediaAsset[]; count: number }>(
      `${API_BASE}/shows/${showId}/media`
    );
    return data.media;
  },

  triggerScrape: (offline = true, maxResults = 50) =>
    fetch(`${API_BASE}/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offline, max_results: maxResults }),
    }).then((r) => r.json()),

  getScrapeStatus: async () => {
    return fetchJSON<{ running: boolean; last_result: unknown }>(`${API_BASE}/scrape/status`);
  },

  runAnalysis: (scope: string, industry?: string, region?: string, show?: string) =>
    fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, industry, region, show }),
    }).then((r) => r.json()),
};
