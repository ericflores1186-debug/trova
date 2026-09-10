-- ---------------------------------------------------------------------------
-- Trova -- store the destination IATA code on flight links
--
-- Run in the Supabase SQL editor after the other schema files. Safe to re-run.
--
-- Aviasales deeplinks are origin-first: `?params=NYCCHC1` means New York to
-- Christchurch. A destination on its own is read as the ORIGIN, which fills
-- the form backwards, and the /search/ results URL errors outright without
-- dates.
--
-- Origin is the visitor's home airport, so it can only be resolved in their
-- browser. Storing the destination IATA lets the storefront page assemble the
-- correct link at click time.
-- ---------------------------------------------------------------------------

alter table public.flight_links
  add column if not exists destination_iata text;

comment on column public.flight_links.destination_iata is
  'IATA code of the destination city, used to build an Aviasales deeplink in the browser.';
