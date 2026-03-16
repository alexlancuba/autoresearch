import type { Stats, AnalysisCycle } from "../types";

interface SidebarProps {
  industries: string[];
  regions: string[];
  selectedIndustry: string;
  selectedRegion: string;
  tradeShowFilter: string;
  onIndustryChange: (v: string) => void;
  onRegionChange: (v: string) => void;
  onTradeShowChange: (v: string) => void;
  onRunAnalysis: () => void;
  onResetFilters: () => void;
  stats: Stats | null;
  cycles: AnalysisCycle[];
}

function formatTime(timestamp: string): string {
  const d = new Date(timestamp);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function Sidebar({
  industries,
  regions,
  selectedIndustry,
  selectedRegion,
  tradeShowFilter,
  onIndustryChange,
  onRegionChange,
  onTradeShowChange,
  onRunAnalysis,
  onResetFilters,
  stats,
  cycles,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-section-title">Analysis Controls</div>

        <div>
          <div className="sidebar-label">Industry</div>
          <select
            className="sidebar-select"
            value={selectedIndustry}
            onChange={(e) => onIndustryChange(e.target.value)}
          >
            <option value="">All Industries</option>
            {industries.map((ind) => (
              <option key={ind} value={ind}>
                {ind}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="sidebar-label">Region</div>
          <select
            className="sidebar-select"
            value={selectedRegion}
            onChange={(e) => onRegionChange(e.target.value)}
          >
            <option value="">All Regions</option>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="sidebar-label">Trade Show</div>
          <input
            className="sidebar-input"
            type="text"
            placeholder="e.g. CES, MWC, GITEX..."
            value={tradeShowFilter}
            onChange={(e) => onTradeShowChange(e.target.value)}
          />
        </div>

        <button className="btn-primary" onClick={onRunAnalysis}>
          Run Analysis
        </button>
        <button className="btn-secondary" onClick={onResetFilters}>
          Reset Filters
        </button>
      </div>

      {stats && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Agent Status</div>
          <div className="agent-status">
            <div className="stat-box">
              <div className="stat-value">{stats.total_signals}</div>
              <div className="stat-label">Signals</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">{stats.total_cycles}</div>
              <div className="stat-label">Cycles</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">{stats.total_industries}</div>
              <div className="stat-label">Industries</div>
            </div>
            <div className="stat-box">
              <div className="stat-value">{stats.total_regions}</div>
              <div className="stat-label">Regions</div>
            </div>
          </div>
        </div>
      )}

      {cycles.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Run History</div>
          <div className="run-history">
            {cycles.map((cycle) => (
              <div key={cycle.id} className="run-entry">
                <span className="run-time">{formatTime(cycle.timestamp)}</span>
                <span className="run-scope">{cycle.scope}</span>
                <span className="run-signals">{cycle.signal_count} signals</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
