import type { Trend, Signal, TradeShow, AnalysisCycle, Stats } from "./types";

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

  runAnalysis: (scope: string, industry?: string, region?: string, show?: string) =>
    fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope, industry, region, show }),
    }).then((r) => r.json()),
};
