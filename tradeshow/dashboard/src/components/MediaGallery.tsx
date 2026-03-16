import { useState } from "react";
import type { MediaAsset } from "../types";

interface Props {
  media: MediaAsset[];
  title?: string;
}

const TYPE_LABELS: Record<string, string> = {
  photo: "Photos",
  video: "Videos",
  thumbnail: "Thumbnails",
  floor_plan: "Floor Plans",
  render: "Renders",
};

export function MediaGallery({ media, title }: Props) {
  const [filter, setFilter] = useState<string>("all");
  const [lightbox, setLightbox] = useState<MediaAsset | null>(null);

  const types = Array.from(new Set(media.map((m) => m.media_type)));
  const filtered = filter === "all" ? media : media.filter((m) => m.media_type === filter);

  return (
    <div className="media-gallery">
      {title && <h3 className="gallery-title">{title}</h3>}

      {types.length > 1 && (
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
              {TYPE_LABELS[t] || t} ({media.filter((m) => m.media_type === t).length})
            </button>
          ))}
        </div>
      )}

      <div className="gallery-grid">
        {filtered.map((asset) => (
          <div
            key={asset.id}
            className="gallery-item"
            onClick={() => setLightbox(asset)}
          >
            <div className="gallery-image-wrapper">
              <img
                src={asset.thumbnail_url || asset.url}
                alt={asset.caption}
                loading="lazy"
              />
              {asset.media_type === "video" && (
                <div className="gallery-play-badge">&#9654;</div>
              )}
            </div>
            <div className="gallery-item-info">
              <span className="gallery-item-caption">{asset.caption}</span>
              <div className="gallery-item-tags">
                {asset.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="tag tag-industry">{tag}</span>
                ))}
                <span className="gallery-item-source">{asset.source}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="gallery-empty">
          No media assets yet. Run a scrape to collect booth photos and videos.
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
