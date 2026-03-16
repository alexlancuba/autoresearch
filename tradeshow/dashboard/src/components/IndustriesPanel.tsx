import type { Trend } from "../types";

interface Props {
  trends: Trend[];
  industries: string[];
}

export function IndustriesPanel({ trends, industries }: Props) {
  const industryData = industries.map((ind) => {
    const relevant = trends.filter((t) => t.industries.includes(ind));
    const topTrends = relevant
      .sort((a, b) => b.composite_score - a.composite_score)
      .slice(0, 3);
    return { name: ind, trendCount: relevant.length, topTrends };
  });

  industryData.sort((a, b) => b.trendCount - a.trendCount);

  return (
    <div className="industry-grid">
      {industryData.map((ind) => (
        <div key={ind.name} className="industry-card">
          <div className="industry-card-header">
            <span className="industry-card-name">{ind.name}</span>
            <span className="industry-card-count">
              {ind.trendCount} trend{ind.trendCount !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="industry-card-trends">
            {ind.topTrends.length > 0 ? (
              <>
                Top:{" "}
                {ind.topTrends.map((t, i) => (
                  <span key={t.id}>
                    {t.name} ({t.composite_score.toFixed(1)})
                    {i < ind.topTrends.length - 1 ? ", " : ""}
                  </span>
                ))}
              </>
            ) : (
              <span style={{ color: "var(--text-muted)" }}>No trends detected</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
