import { useState, useEffect, useCallback } from "react";
import type { Trend, TradeShow, AnalysisCycle, Stats, TabId } from "./types";
import { api } from "./api";
import { Sidebar } from "./components/Sidebar";
import { TrendCard } from "./components/TrendCard";
import { IndustriesPanel } from "./components/IndustriesPanel";
import { RegionsPanel } from "./components/RegionsPanel";
import { OpportunitiesPanel } from "./components/OpportunitiesPanel";
import { TradeShowsPanel } from "./components/TradeShowsPanel";

const TABS: { id: TabId; label: string }[] = [
  { id: "top-trends", label: "Top Trends" },
  { id: "industries", label: "Industries" },
  { id: "regions", label: "Regions" },
  { id: "opportunities", label: "Opportunities" },
  { id: "trade-shows", label: "Trade Shows" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("top-trends");
  const [trends, setTrends] = useState<Trend[]>([]);
  const [shows, setShows] = useState<TradeShow[]>([]);
  const [cycles, setCycles] = useState<AnalysisCycle[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [industries, setIndustries] = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [selectedIndustry, setSelectedIndustry] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("");
  const [tradeShowFilter, setTradeShowFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [t, s, c, st, ind, reg] = await Promise.all([
        api.getTrends(selectedIndustry, selectedRegion),
        api.getShows(selectedIndustry, selectedRegion),
        api.getCycles(),
        api.getStats(),
        api.getIndustries(),
        api.getRegions(),
      ]);
      setTrends(t);
      setShows(s);
      setCycles(c);
      setStats(st);
      setIndustries(ind);
      setRegions(reg);
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedIndustry, selectedRegion]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunAnalysis = async () => {
    const scope = tradeShowFilter || (selectedRegion || "Full Scan");
    await api.runAnalysis(scope, selectedIndustry, selectedRegion, tradeShowFilter);
    loadData();
  };

  const handleResetFilters = () => {
    setSelectedIndustry("");
    setSelectedRegion("");
    setTradeShowFilter("");
  };

  return (
    <div className="app-layout">
      <Sidebar
        industries={industries}
        regions={regions}
        selectedIndustry={selectedIndustry}
        selectedRegion={selectedRegion}
        tradeShowFilter={tradeShowFilter}
        onIndustryChange={setSelectedIndustry}
        onRegionChange={setSelectedRegion}
        onTradeShowChange={setTradeShowFilter}
        onRunAnalysis={handleRunAnalysis}
        onResetFilters={handleResetFilters}
        stats={stats}
        cycles={cycles}
      />
      <div className="main-content">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div className="app-header">
            <div className="app-icon">TS</div>
            <h1 className="app-title">Trade Show Trend Analysis</h1>
          </div>
          <div className="header-badges">
            <span className="badge badge-preview">Preview Mode</span>
            <span className="badge badge-ready">READY</span>
          </div>
        </div>

        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
            Loading analysis data...
          </div>
        ) : (
          <div className="panel">
            {activeTab === "top-trends" && (
              <div className="trend-list">
                {trends.map((trend) => (
                  <TrendCard key={trend.id} trend={trend} />
                ))}
              </div>
            )}
            {activeTab === "industries" && (
              <IndustriesPanel trends={trends} industries={industries} />
            )}
            {activeTab === "regions" && (
              <RegionsPanel trends={trends} regions={regions} />
            )}
            {activeTab === "opportunities" && (
              <OpportunitiesPanel trends={trends} />
            )}
            {activeTab === "trade-shows" && (
              <TradeShowsPanel shows={shows} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
