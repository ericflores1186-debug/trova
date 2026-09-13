-- ---------------------------------------------------------------------------
-- Trova -- TikTok support
--
-- Run in the Supabase SQL editor after the other schema files. Safe to re-run.
-- ---------------------------------------------------------------------------

-- A TikTok account and a YouTube channel with the same handle are not
-- necessarily the same person, and treating them as one creator would merge
-- two people's earnings. So each platform keys creators on its own column.
alter table public.creators
  add column if not exists tiktok_handle text;

create unique index if not exists creators_tiktok_handle_key
  on public.creators (tiktok_handle)
  where tiktok_handle is not null;

-- A YouTube thumbnail is derived from the video ID and never expires. TikTok's
-- cover links are signed and stop working after two days, so the backend
-- copies the image into storage and saves the permanent address here.
alter table public.storefronts
  add column if not exists thumbnail_url text;

-- Public bucket: anyone can view a cover, and only the backend -- whose secret
-- key bypasses row level security -- can upload one. So no storage policies
-- are needed in either direction.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'video-covers',
  'video-covers',
  true,
  2097152, -- 2 MB; a TikTok cover is usually under 300 KB
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;
