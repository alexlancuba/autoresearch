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

export interface Stats {
  total_signals: number;
  total_cycles: number;
  total_industries: number;
  total_regions: number;
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

export type TabId =
  | "top-trends"
  | "industries"
  | "regions"
  | "opportunities"
  | "trade-shows"
  | "visuals";
