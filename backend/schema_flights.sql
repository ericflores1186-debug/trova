-- ---------------------------------------------------------------------------
-- Trova -- flights migration
--
-- Adds flight affiliate links alongside hotels. Run this in the Supabase SQL
-- editor after schema.sql. Safe to re-run.
--
-- Flights live in their own table rather than sharing `affiliate_links`: a
-- flight has an origin and a destination, a hotel has a name and a location,
-- and forcing both into one shape makes every query ambiguous.
-- ---------------------------------------------------------------------------

create table if not exists public.flight_links (
  id                  uuid primary key default gen_random_uuid(),
  storefront_id       uuid not null references public.storefronts(id) on delete cascade,
  destination_city    text not null,
  destination_country text,
  origin_city         text,
  airline             text,
  booking_url         text not null,
  created_at          timestamptz not null default now()
);

create index if not exists flight_links_storefront_id_idx
  on public.flight_links (storefront_id);

-- Same policy as the other tables: public read, writes only via the backend's
-- secret key (which bypasses RLS).
alter table public.flight_links enable row level security;

drop policy if exists "public read flight_links" on public.flight_links;
create policy "public read flight_links"
  on public.flight_links for select to anon, authenticated using (true);
