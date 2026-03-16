import { useRef } from "react";
import type { MediaAsset } from "../types";

interface Props {
  media: MediaAsset[];
  onImageClick?: (asset: MediaAsset) => void;
}

export function MediaCarousel({ media, onImageClick }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  if (media.length === 0) return null;

  const scroll = (dir: "left" | "right") => {
    if (!scrollRef.current) return;
    const amount = dir === "left" ? -240 : 240;
    scrollRef.current.scrollBy({ left: amount, behavior: "smooth" });
  };

  return (
    <div className="media-carousel">
      {media.length > 3 && (
        <button className="carousel-btn carousel-btn-left" onClick={() => scroll("left")}>
          &#8249;
        </button>
      )}
      <div className="carousel-track" ref={scrollRef}>
        {media.map((asset) => (
          <div
            key={asset.id}
            className="carousel-item"
            onClick={() => onImageClick?.(asset)}
          >
            {asset.media_type === "video" ? (
              <div className="carousel-video-thumb">
                <img
                  src={asset.thumbnail_url || asset.url}
                  alt={asset.caption}
                  loading="lazy"
                />
                <div className="carousel-play-icon">&#9654;</div>
              </div>
            ) : (
              <img
                src={asset.thumbnail_url || asset.url}
                alt={asset.caption}
                loading="lazy"
              />
            )}
            <div className="carousel-caption">{asset.caption}</div>
          </div>
        ))}
      </div>
      {media.length > 3 && (
        <button className="carousel-btn carousel-btn-right" onClick={() => scroll("right")}>
          &#8250;
        </button>
      )}
    </div>
  );
}
