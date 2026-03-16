import { useState, useEffect } from "react";
import type { MediaAsset } from "../types";
import { api } from "../api";

export function VisualBoardPanel() {
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<MediaAsset | null>(null);

  useEffect(() => {
    api.getMedia().then((m) => {
      setMedia(m);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const types = Array.from(new Set(media.map((m) => m.media_type)));
  const filtered = filter === "all" ? media : media.filter((m) => m.media_type === filter);

  // Group by trade show for masonry sections
  const byShow: Record<string, MediaAsset[]> = {};
  for (const m of filtered) {
    for (const show of m.trade_shows) {
      if (!byShow[show]) byShow[show] = [];
      byShow[show].push(m);
    }
    if (m.trade_shows.length === 0) {
      if (!byShow["Uncategorized"]) byShow["Uncategorized"] = [];
      byShow["Uncategorized"].push(m);
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
        Loading visual media...
      </div>
    );
  }

  return (
    <div className="visual-board">
      <div className="visual-board-header">
        <h2 className="visual-board-title">Visual Inspiration Board</h2>
        <p className="visual-board-subtitle">
          Booth photos, video walkthroughs, and design references from trade shows worldwide
        </p>
      </div>

      {types.length > 0 && (
        <div className="gallery-filters">
          <button
            className={`gallery-filter ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All ({media.length})
          </button>
          {types.map((t) => (
            <button
              key={t}
              className={`gallery-filter ${filter === t ? "active" : ""}`}
              onClick={() => setFilter(t)}
            >
              {t} ({media.filter((m) => m.media_type === t).length})
            </button>
          ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="visual-board-empty">
          <div className="visual-board-empty-icon">&#128247;</div>
          <h3>No Visual Media Yet</h3>
          <p>
            Run a data collection scrape to fetch booth tour videos, exhibit photos,
            and design references from YouTube, trade show galleries, and news sources.
          </p>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
            Use the "Run Analysis" button in the sidebar or trigger via POST /api/scrape
          </p>
        </div>
      ) : (
        <div className="masonry-grid">
          {filtered.map((asset) => (
            <div
              key={asset.id}
              className="masonry-item"
              onClick={() => setLightbox(asset)}
            >
              <img
                src={asset.thumbnail_url || asset.url}
                alt={asset.caption}
                loading="lazy"
              />
              {asset.media_type === "video" && (
                <div className="masonry-play-badge">&#9654;</div>
              )}
              <div className="masonry-overlay">
                <span className="masonry-caption">{asset.caption}</span>
                <div className="masonry-tags">
                  {asset.trade_shows.slice(0, 2).map((s) => (
                    <span key={s} className="tag tag-scope">{s}</span>
                  ))}
                  {asset.tags.slice(0, 2).map((tag) => (
                    <span key={tag} className="tag tag-industry">{tag}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {lightbox && (
        <div className="lightbox-overlay" onClick={() => setLightbox(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setLightbox(null)}>
              &times;
            </button>
            {lightbox.media_type === "video" ? (
              <iframe
                src={lightbox.url}
                title={lightbox.caption}
                className="lightbox-video"
                allowFullScreen
              />
            ) : (
              <img src={lightbox.url} alt={lightbox.caption} className="lightbox-image" />
            )}
            <div className="lightbox-info">
              <p className="lightbox-caption">{lightbox.caption}</p>
              <div className="lightbox-meta">
                {lightbox.trade_shows.map((s) => (
                  <span key={s} className="tag tag-scope">{s}</span>
                ))}
              </div>
              {lightbox.source_url && (
                <a
                  href={lightbox.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lightbox-link"
                >
                  View source
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
