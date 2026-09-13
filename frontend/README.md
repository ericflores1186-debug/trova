# Trova — Frontend (Phase 2)

Next.js App Router front end for Trova. A creator pastes a YouTube, TikTok or Instagram link, the
FastAPI backend builds the storefront, and the public storefront page reads it
straight from Supabase.

## Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local     # then fill in your keys
npm run dev
```

Open http://localhost:3000. The Phase 1 backend must be running on
`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) for storefront
generation to work.

## Routes

| Route | Rendering | What it does |
| --- | --- | --- |
| `/` | Dynamic | Dashboard. URL input, staged loading state, recent storefronts |
| `/[storefrontId]` | Dynamic | Public storefront. Hotel cards + booking links |

Both are `force-dynamic`: a storefront is usually opened seconds after it is
created, so a build-time cache would 404.

## Data flow

```
Dashboard  ──POST /api/generate-storefront──▶  FastAPI  ──▶  Supabase
    │                                                          │
    └──router.push(`/${storefront_id}`)──▶  Storefront page ────┘
                                            (reads Supabase directly, publishable key)
```

Writes go through FastAPI, which holds the secret key server-side. The
browser only ever holds the publishable key, and `schema.sql` restricts that key to
`SELECT` through Row Level Security.

**Never put `SUPABASE_SECRET_KEY` in a `NEXT_PUBLIC_*` variable.** Anything
prefixed `NEXT_PUBLIC_` is inlined into the client bundle.

## Layout

```
app/
  layout.tsx                 Root layout, Instrument Serif display font
  globals.css                Tailwind v4 + Trova design tokens (@theme)
  page.tsx                   Dashboard
  [storefrontId]/
    page.tsx                 Public storefront + generateMetadata (OG tags)
    not-found.tsx            404 state
  components/
    StorefrontForm.tsx       'use client' — validation, staged progress, errors
    HotelCard.tsx            Hotel card with rel="sponsored" booking link
    ShareButton.tsx          'use client' — Web Share / clipboard fallback
    Wordmark.tsx             Trova wordmark
  lib/
    api.ts                   FastAPI client + typed error
    supabase.ts              Lazy anon-key client
    storefronts.ts           Storefront queries
    youtube.ts               URL → video ID, thumbnail URL
    video.ts                 Which platform a link is: YouTube, TikTok or Instagram
    types.ts                 Mirrors the backend Pydantic models
```

## Design tokens

Defined once in `globals.css` under `@theme`, so they generate Tailwind
utilities (`bg-paper`, `text-ink-soft`, `border-sand`, `font-display`):

| Token | Value | Use |
| --- | --- | --- |
| `paper` / `paper-raised` | `#fbf8f3` / `#ffffff` | Page ground, cards |
| `sand` / `sand-deep` | `#ece3d6` / `#ddd0bd` | Borders, disabled states |
| `ink` / `ink-soft` / `ink-faint` | `#191512` / `#5c524a` / `#8d8177` | Text hierarchy |
| `clay` / `clay-deep` / `clay-wash` | `#c25e3a` / `#a44a2a` / `#f7ece5` | Accent, CTAs, errors |
| `moss` | `#3f5a45` | Success ticks |

## Notes

- **Tailwind v4** — configuration lives in `globals.css` via `@theme`. There is
  no `tailwind.config.ts`.
- **Loading state** — the backend runs the whole pipeline as one request, so
  there is no server-sent progress. The stepper in `StorefrontForm.tsx`
  advances on elapsed time and holds on the last step until the response lands.
  If you later stream progress from the backend, that is the one component to
  change.
- **Affiliate compliance** — booking links use `rel="sponsored"` and both pages
  carry a disclosure in the footer.
