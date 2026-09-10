-- ---------------------------------------------------------------------------
-- Trova -- outbound click tracking
--
-- Run in the Supabase SQL editor after the other schema files. Safe to re-run.
--
-- Records when someone clicks through to book. Creators cannot see their
-- Travelpayouts earnings from inside Trova (the commission lands in their own
-- account), so click-through is the only value signal Trova can show them --
-- and it is what makes a subscription justifiable.
--
-- Deliberately stores no IP address and no cookie. Referrer and user agent are
-- enough for "how many people clicked, and from where", and anything more
-- would make this a privacy liability for a feature that does not need one.
-- ---------------------------------------------------------------------------

create table if not exists public.link_clicks (
  id            uuid primary key default gen_random_uuid(),
  storefront_id uuid not null references public.storefronts(id) on delete cascade,
  link_id       uuid not null,
  link_type     text not null check (link_type in ('hotel', 'flight')),
  clicked_at    timestamptz not null default now(),
  referrer      text,
  user_agent    text
);

create index if not exists link_clicks_storefront_idx
  on public.link_clicks (storefront_id, clicked_at desc);

create index if not exists link_clicks_link_idx
  on public.link_clicks (link_id);

alter table public.link_clicks enable row level security;

-- No public policy at all: clicks are written by the backend with the secret
-- key, and read back through the stats endpoint. Nothing in the browser needs
-- direct access, and letting anon read them would expose one creator's
-- performance to another.
