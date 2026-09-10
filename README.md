# Trova

Turn a travel video into a bookable storefront. Paste a YouTube link, and Trova
reads the transcript, finds every hotel the creator named, and builds a
shareable page with an affiliate booking link for each stay.

```
frontend/   Next.js App Router + Tailwind v4   (see frontend/README.md)
backend/    FastAPI + Claude + Supabase        (see backend/README.md)
```

## Quick start

**1. Database** — run [`backend/schema.sql`](backend/schema.sql) in the Supabase
SQL editor. It creates `creators`, `storefronts`, `affiliate_links` and enables
RLS with public read / no public write.

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

Open http://localhost:3000.

## How a storefront gets built

```
  YouTube URL
      │
      ▼
  youtube-transcript-api ──▶ transcript text
      │
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
