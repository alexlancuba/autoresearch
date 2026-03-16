import type { Trend } from "../types";

interface Opportunity {
  type: "whitespace" | "convergence" | "acceleration";
  name: string;
  description: string;
  relatedTrends: string[];
}

function deriveOpportunities(trends: Trend[]): Opportunity[] {
  const opportunities: Opportunity[] = [];

  // Whitespace: emerging trends with high velocity
  const emerging = trends.filter((t) => t.lifecycle === "emerging");
  for (const t of emerging) {
    opportunities.push({
      type: "whitespace",
      name: `Early Mover: ${t.name}`,
      description: `${t.name} is in early stages (score ${t.composite_score.toFixed(1)}) with ${Math.round(t.confidence * 100)}% confidence. Exhibitors who invest in this space now can establish thought leadership before the trend matures. Design opportunity: create immersive demonstrations that make abstract concepts tangible for attendees.`,
      relatedTrends: [t.name],
    });
  }

  // Convergence: cross-industry trends appearing in 4+ industries
  const crossIndustry = trends.filter(
    (t) => t.cross_industry && t.industries.length >= 4
  );
  for (const t of crossIndustry.slice(0, 3)) {
    opportunities.push({
      type: "convergence",
      name: `Cross-Industry Convergence: ${t.name}`,
      description: `${t.name} spans ${t.industries.length} industries with ${t.mention_count} mentions across ${t.show_count} events. Companies that position their booth narrative around this cross-cutting theme can attract visitors from adjacent industries and expand their prospect universe.`,
      relatedTrends: [t.name],
    });
  }

  // Acceleration: growing trends with high scores
  const accelerating = trends
    .filter((t) => t.lifecycle === "growing" && t.composite_score >= 35)
    .slice(0, 3);
  for (const t of accelerating) {
    opportunities.push({
      type: "acceleration",
      name: `Accelerating Trend: ${t.name}`,
      description: `${t.name} is accelerating with a composite score of ${t.composite_score.toFixed(1)} and ${Math.round(t.confidence * 100)}% confidence. Exhibitors in this space should differentiate through design — move beyond product displays to interactive workflow simulations that demonstrate real-world application of ${t.keywords.slice(0, 2).join(" and ")}.`,
      relatedTrends: [t.name],
    });
  }

  return opportunities;
}

export function OpportunitiesPanel({ trends }: { trends: Trend[] }) {
  const opportunities = deriveOpportunities(trends);

  return (
    <div className="opportunity-list">
      {opportunities.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
          Run an analysis to discover opportunities.
        </div>
      ) : (
        opportunities.map((opp, i) => (
          <div key={i} className="opportunity-card">
            <div className="opportunity-header">
              <span className={`opportunity-type ${opp.type}`}>{opp.type}</span>
              <span className="opportunity-name">{opp.name}</span>
            </div>
            <div className="opportunity-description">{opp.description}</div>
            <div style={{ marginTop: 8 }}>
              <div className="trend-tags">
                {opp.relatedTrends.map((t) => (
                  <span key={t} className="tag tag-industry">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
