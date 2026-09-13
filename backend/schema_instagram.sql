-- ---------------------------------------------------------------------------
-- Trova -- Instagram support
--
-- Run in the Supabase SQL editor after schema_tiktok.sql, which creates the
-- storefronts.thumbnail_url column and the video-covers bucket that Instagram
-- covers are stored in too. Safe to re-run.
-- ---------------------------------------------------------------------------

-- As with TikTok: an Instagram account and a YouTube or TikTok account with
-- the same handle are not necessarily the same person, and merging them would
-- merge two people's earnings. So Instagram keys creators on its own column.
alter table public.creators
  add column if not exists instagram_handle text;

create unique index if not exists creators_instagram_handle_key
  on public.creators (instagram_handle)
  where instagram_handle is not null;
