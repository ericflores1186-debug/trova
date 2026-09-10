-- ---------------------------------------------------------------------------
-- Trova -- per-creator affiliate markers
--
-- Run in the Supabase SQL editor after schema.sql and schema_flights.sql.
-- Safe to re-run.
--
-- Until now every booking link carried one platform-wide marker, so all
-- commission went to whoever runs Trova. Storing a marker per creator means
-- each creator's storefronts pay that creator.
--
-- The marker is copied onto the storefront at creation time rather than read
-- from the creator on every page view. If a creator later changes their
-- marker, links already published keep paying the marker that was in force
-- when they were made -- which is what a creator expects, and avoids
-- rewriting live URLs underneath people.
-- ---------------------------------------------------------------------------

alter table public.creators
  add column if not exists travelpayouts_marker text;

comment on column public.creators.travelpayouts_marker is
  'The creator''s own Travelpayouts marker. Null means fall back to the platform marker.';

-- Record of which marker a given storefront's links were built with, for
-- support questions like "why did this booking not pay me?".
alter table public.storefronts
  add column if not exists marker_used text;

comment on column public.storefronts.marker_used is
  'The Travelpayouts marker embedded in this storefront''s links at creation.';
