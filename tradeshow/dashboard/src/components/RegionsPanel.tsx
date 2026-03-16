import type { Trend } from "../types";

interface Props {
  trends: Trend[];
  regions: string[];
}

export function RegionsPanel({ trends, regions }: Props) {
  const regionData = regions.map((reg) => {
    const relevant = trends.filter((t) => t.regions.includes(reg));
    const topTrends = relevant
      .sort((a, b) => b.composite_score - a.composite_score)
      .slice(0, 5);
    const avgScore =
      relevant.length > 0
        ? relevant.reduce((s, t) => s + t.composite_score, 0) / relevant.length
        : 0;
    return { name: reg, trendCount: relevant.length, topTrends, avgScore };
  });

  regionData.sort((a, b) => b.trendCount - a.trendCount);

  return (
    <div className="region-grid">
      {regionData.map((reg) => (
        <div key={reg.name} className="region-card">
          <div className="region-card-header">
            <span className="region-card-name">{reg.name}</span>
            <span className="region-card-count">
              {reg.trendCount} trend{reg.trendCount !== 1 ? "s" : ""} | Avg:{" "}
              {reg.avgScore.toFixed(1)}
            </span>
          </div>
          <div className="trend-list" style={{ gap: 6 }}>
            {reg.topTrends.map((t) => (
              <div
                key={t.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "6px 0",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 12,
                }}
              >
                <span>
                  <span style={{ color: "var(--text-muted)", marginRight: 6 }}>
                    #{t.rank}
                  </span>
                  {t.name}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    color:
                      t.composite_score >= 40
                        ? "var(--accent-green)"
                        : t.composite_score >= 25
                        ? "var(--accent-orange)"
                        : "var(--accent-purple)",
                  }}
                >
                  {t.composite_score.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
