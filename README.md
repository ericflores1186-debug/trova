# Trova

Turn a travel video into a bookable storefront. Paste a YouTube, TikTok or
Instagram link, and Trova reads the post, finds every hotel the creator named and
every city they flew to, and builds a shareable page with an affiliate booking
link for each.

**Live at [trovastays.app](https://trovastays.app).**

```
frontend/   Next.js App Router + Tailwind v4   (see frontend/README.md)
backend/    FastAPI + Claude + Supabase        (see backend/README.md)
```

## Quick start

**1. Database** — run these in the Supabase SQL editor, in order. Each is safe
to re-run.

| File | Adds |
| --- | --- |
| [`schema.sql`](backend/schema.sql) | `creators`, `storefronts`, `affiliate_links`, RLS |
| [`schema_flights.sql`](backend/schema_flights.sql) | `flight_links` |
| [`schema_flight_iata.sql`](backend/schema_flight_iata.sql) | destination IATA codes |
| [`schema_creator_marker.sql`](backend/schema_creator_marker.sql) | per-creator markers |
| [`schema_subid.sql`](backend/schema_subid.sql) | per-creator SubIDs |
| [`schema_clicks.sql`](backend/schema_clicks.sql) | outbound click tracking |
| [`schema_tiktok.sql`](backend/schema_tiktok.sql) | TikTok handles, cover images + `video-covers` bucket |
| [`schema_instagram.sql`](backend/schema_instagram.sql) | Instagram handles |

**2. Backend**

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in Supabase + Anthropic keys
uvicorn app.main:app --reload --port 8000
```

**3. Frontend**

```bash
cd frontend && npm install
cp .env.local.example .env.local   # fill in Supabase URL + PUBLISHABLE key
npm run dev
```

Open http://localhost:3000. Production runs at trovastays.app.

## How a storefront gets built

```
  YouTube URL              TikTok URL                     Instagram URL
      │                        │                               │
      ▼                        ▼                               ▼
  youtube-transcript-api   post page: caption, on-screen   embed page: caption,
      │  transcript text   text, tagged location, spoken   cover or carousel
      │                    captions, slideshow images      images (no audio)
      └────────────────────────┬───────────────────────────────┘
                               ▼
  Claude (structured outputs) ──▶ [{ hotel_name, location }, ...]
      │
      ▼
  Travelpayouts ──▶ + booking_url
      │
      ▼
  Supabase ──▶ storefront id ──▶ /[storefrontId]
```

## Keys and where they live

| Key | Lives in | Reaches the browser? |
| --- | --- | --- |
| `SUPABASE_SECRET_KEY` | `backend/.env` | **Never** — bypasses RLS |
| `ANTHROPIC_API_KEY` | `backend/.env` | Never |
| `TRAVELPAYOUTS_API_TOKEN` | `backend/.env` | Never |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | `frontend/.env.local` | Yes — RLS limits it to `SELECT` |

All writes go through FastAPI. The browser only ever reads.
