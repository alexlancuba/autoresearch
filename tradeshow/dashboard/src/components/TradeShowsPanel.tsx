import type { TradeShow } from "../types";

const TIER_LABELS: Record<string, string> = {
  global_flagship: "Global Flagship",
  regional_major: "Regional Major",
  niche: "Niche",
};

export function TradeShowsPanel({ shows }: { shows: TradeShow[] }) {
  const sorted = [...shows].sort((a, b) => {
    const tierOrder: Record<string, number> = { global_flagship: 0, regional_major: 1, niche: 2 };
    return (tierOrder[a.tier] ?? 2) - (tierOrder[b.tier] ?? 2);
  });

  return (
    <div className="show-grid">
      {sorted.map((show) => (
        <div key={show.id} className="show-card">
          <div className="show-card-header">
            <span className="show-card-name">{show.name}</span>
            <span className="show-card-short">{show.short_name}</span>
          </div>
          <div className="show-card-location">
            {show.city}, {show.country} &middot; {show.region}
          </div>
          <div className="show-card-meta">
            <span>{TIER_LABELS[show.tier] ?? show.tier}</span>
            <span>{show.frequency}</span>
            {show.typical_exhibitors > 0 && (
              <span>{show.typical_exhibitors.toLocaleString()} exhibitors</span>
            )}
            {show.typical_attendees > 0 && (
              <span>{show.typical_attendees.toLocaleString()} attendees</span>
            )}
          </div>
          <div className="show-card-tags">
            {show.industries.slice(0, 3).map((ind) => (
              <span key={ind} className="tag tag-industry">
                {ind}
              </span>
            ))}
            {show.industries.length > 3 && (
              <span className="tag tag-industry">+{show.industries.length - 3}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
