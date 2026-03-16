# Trade Show Trend Analysis — Frontend Integration Guide

## Quick Start

1. Set your environment variable to point at the backend API:
   ```
   VITE_API_BASE_URL=https://your-backend.up.railway.app
   ```

2. Copy `api-client.ts` into your Lovable project's `src/lib/` directory.

3. Import and use:
   ```tsx
   import { api } from "@/lib/api-client";
   const trends = await api.getTrends();
   ```

4. Visit `{VITE_API_BASE_URL}/docs` for interactive Swagger documentation.

---

## API Base URL

| Environment | URL |
|-------------|-----|
| Local dev | `http://localhost:8000` |
| Production | Set via `VITE_API_BASE_URL` env var |

All endpoints are under `/api/v1/`. The Swagger docs at `/docs` show every endpoint with types.

---

## Component → API Mapping

Use this table to know which API calls each dashboard view needs:

| View / Component | API Endpoints | Key Fields |
|-----------------|---------------|------------|
| **Trend Cards** | `GET /api/v1/trends` | rank, name, composite_score, lifecycle, confidence, industries, regions, keywords, description |
| **Trend Detail + Media** | `GET /api/v1/trends/{id}`, `GET /api/v1/trends/{id}/media` | All trend fields + media thumbnails |
| **Sidebar Stats** | `GET /api/v1/stats` | total_signals, total_trends, total_shows, total_cycles, total_media |
| **Sidebar Filters** | `GET /api/v1/industries`, `GET /api/v1/regions` | Industry and region name lists |
| **Run History** | `GET /api/v1/cycles` | id, timestamp, scope, signal_count |
| **Industries Panel** | `GET /api/v1/trends` | Group by industries array, count per industry |
| **Regions Panel** | `GET /api/v1/trends` | Group by regions array, avg score per region |
| **Opportunities** | `GET /api/v1/trends` | Derive from lifecycle + velocity + cross_industry + industries.length |
| **Trade Shows** | `GET /api/v1/shows` | name, short_name, tier, city, country, industries |
| **Show Media** | `GET /api/v1/shows/{id}/media` | Media assets for a specific show |
| **Visuals Board** | `GET /api/v1/media` | url, thumbnail_url, media_type, caption, tags, trade_shows |
| **Media Carousel** | `GET /api/v1/trends/{id}/media` | Inline thumbnails per trend |
| **Run Analysis** | `POST /api/v1/analyze` | Send scope/industry/region/show, receive updated cycle + trends |
| **Trigger Scrape** | `POST /api/v1/scrape` | Send offline/max_results, receive status |
| **Backend Health** | `GET /api/v1/health` | status, version, data_counts, uptime_seconds |

---

## Data Types

All TypeScript interfaces are in `api-client.ts`. Key types:

- **Trend** — Ranked trend with composite_score (0-100), confidence (0-1), lifecycle stage
- **Signal** — Raw observation with strength (0-1), source_type, trade_shows
- **TradeShow** — Event with tier, location, industry tags
- **MediaAsset** — Photo/video/thumbnail with source URL, tags, trade show associations
- **AnalysisCycle** — Run history entry with signal/trend counts
- **Stats** — Dashboard overview counts

---

## Pagination

List endpoints support optional pagination:
```
GET /api/v1/trends?page=1&page_size=25
```

Response includes `page`, `page_size`, and `total` when pagination is used.
Omit these params to get all results (backward compatible).

---

## Filtering

Most list endpoints accept query parameters:
- `industry` — Filter by industry name (e.g., "Technology & Electronics")
- `region` — Filter by region name (e.g., "North America")
- `trend_category` — Filter signals by trend category
- `cycle_id` — Filter by analysis cycle ID
- `trade_show` — Filter media by trade show short name
- `media_type` — Filter media by type (photo, video, thumbnail, floor_plan, render)

---

## Design Tokens

See `design-tokens.json` for the current color palette, typography, and spacing.
These are starting points — feel free to evolve them in Lovable.

Key colors:
- Background: `#0d1117` (dark), `#161b22` (sidebar), `#1a1f2e` (cards)
- Text: `#e6edf3` (primary), `#8b949e` (secondary), `#6e7681` (muted)
- Accents: Blue `#388bfd`, Green `#3fb950`, Purple `#a371f7`, Orange `#d29922`
- Lifecycle badges: Emerging (purple), Growing (green), Mature (blue), Declining (red)

---

## Auth

Currently no authentication is required. The API accepts an optional `Authorization` header
that is passed through but not validated. When auth is enabled on the backend, add:
```ts
headers: { "Authorization": `Bearer ${token}` }
```
to all fetch calls. The `api-client.ts` has a commented placeholder for this.
