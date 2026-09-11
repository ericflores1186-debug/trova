-- ---------------------------------------------------------------------------
-- Trova -- per-creator SubIDs
--
-- Run in the Supabase SQL editor after the other schema files. Safe to re-run.
--
-- Travelpayouts pays one account per marker, so a revenue split is impossible
-- at the link level. Instead every link carries Trova's marker with a SubID
-- identifying the creator: "marker=572600.wanderlust". Travelpayouts pays
-- Trova, its Performance report breaks earnings down by SubID, and Trova pays
-- each creator their share.
--
-- Creators need no Travelpayouts account at all, and their first payout is not
-- gated behind clearing Travelpayouts' own minimum on their own bookings --
-- which varies by payout method, $50 for PayPal in their documented example.
--
-- The SubID is stored rather than derived from the handle, so that a creator
-- renaming their channel does not silently break the attribution history of
-- links already published.
-- ---------------------------------------------------------------------------

alter table public.creators
  add column if not exists subid text;

-- Two creators must never share a SubID, or their earnings merge in the report.
create unique index if not exists creators_subid_key
  on public.creators (subid)
  where subid is not null;

comment on column public.creators.subid is
  'Travelpayouts SubID for this creator. Latin letters, digits and underscores only.';
