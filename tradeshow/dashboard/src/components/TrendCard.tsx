import { useState, useEffect } from "react";
import type { Trend, MediaAsset } from "../types";
import { api } from "../api";
import { MediaCarousel } from "./MediaCarousel";

function scoreClass(score: number): string {
  if (score >= 40) return "score-high";
  if (score >= 25) return "score-medium";
  return "score-low";
}

export function TrendCard({ trend }: { trend: Trend }) {
  const [media, setMedia] = useState<MediaAsset[]>([]);

  useEffect(() => {
    api.getTrendMedia(trend.id).then(setMedia).catch(() => {});
  }, [trend.id]);

  return (
    <div className="trend-card">
      <div className="trend-card-header">
        <span className="trend-rank">#{trend.rank}</span>
        <span className="trend-name">{trend.name}</span>
        <span className={`trend-score ${scoreClass(trend.composite_score)}`}>
          {trend.composite_score.toFixed(1)}
        </span>
      </div>

      <div className="trend-tags">
        <span className={`tag tag-lifecycle ${trend.lifecycle}`}>
          {trend.lifecycle}
        </span>
        {trend.cross_industry && (
          <span className="tag tag-cross-industry">Cross-Industry</span>
        )}
        <span className="tag tag-scope">{trend.scope}</span>
        {trend.industries.slice(0, 4).map((ind) => (
          <span key={ind} className="tag tag-industry">
            {ind}
          </span>
        ))}
        {trend.industries.length > 4 && (
          <span className="tag tag-industry">+{trend.industries.length - 4}</span>
        )}
        {trend.regions.slice(0, 3).map((r) => (
          <span key={r} className="tag tag-region">
            {r}
          </span>
        ))}
      </div>

      <div className="trend-description">{trend.description}</div>

      {media.length > 0 && <MediaCarousel media={media} />}

      <div className="trend-meta">
        <div className="trend-meta-left">
          <span>
            {trend.mention_count} mentions across {trend.show_count} events
          </span>
          <span>|</span>
          <span>Confidence: {Math.round(trend.confidence * 100)}%</span>
        </div>
        <div className="trend-keywords">
          {trend.keywords.map((kw) => (
            <span key={kw} className="keyword">
              {kw}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
