-- ---------------------------------------------------------------------------
-- Creator Storefront -- MVP schema
-- Run in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
-- ---------------------------------------------------------------------------

create extension if not exists "pgcrypto";

-- --- creators --------------------------------------------------------------
create table if not exists public.creators (
  id             uuid primary key default gen_random_uuid(),
  name           text not null,
  youtube_handle text unique,
  created_at     timestamptz not null default now()
);

-- --- storefronts -----------------------------------------------------------
create table if not exists public.storefronts (
  id          uuid primary key default gen_random_uuid(),
  creator_id  uuid not null references public.creators(id) on delete cascade,
  video_url   text not null,
  video_title text not null,
  created_at  timestamptz not null default now()
);

create index if not exists storefronts_creator_id_idx
  on public.storefronts (creator_id);

-- --- affiliate_links -------------------------------------------------------
create table if not exists public.affiliate_links (
  id            uuid primary key default gen_random_uuid(),
  storefront_id uuid not null references public.storefronts(id) on delete cascade,
  hotel_name    text not null,
  location      text not null default 'Unknown',
  booking_url   text not null,
  created_at    timestamptz not null default now()
);

create index if not exists affiliate_links_storefront_id_idx
  on public.affiliate_links (storefront_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
--
-- Storefronts are public pages, so the anon key gets SELECT on all three
-- tables. Writes are intentionally NOT granted to anon: only the FastAPI
-- backend writes, and it uses the service-role key, which bypasses RLS.
-- ---------------------------------------------------------------------------

alter table public.creators       enable row level security;
alter table public.storefronts    enable row level security;
alter table public.affiliate_links enable row level security;

drop policy if exists "public read creators" on public.creators;
create policy "public read creators"
  on public.creators for select to anon, authenticated using (true);

drop policy if exists "public read storefronts" on public.storefronts;
create policy "public read storefronts"
  on public.storefronts for select to anon, authenticated using (true);

drop policy if exists "public read affiliate_links" on public.affiliate_links;
create policy "public read affiliate_links"
  on public.affiliate_links for select to anon, authenticated using (true);
