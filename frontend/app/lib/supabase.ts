import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Read-only Supabase client for public storefront pages.
 *
 * Uses the ANON key, which Row Level Security restricts to SELECT (see
 * backend/schema.sql). All writes go through the FastAPI backend, which holds
 * the service-role key server-side. Never import a service-role key here --
 * anything in this file can end up in the browser bundle.
 *
 * Created lazily so a missing key surfaces as a runtime error on the request
 * that needs it, rather than crashing `next build`.
 */
let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  // Supabase is retiring the legacy `anon` JWT in favour of a publishable key
  // (`sb_publishable_...`). Either works today, so accept both names.
  const publishableKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ??
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !publishableKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. " +
        "Copy .env.local.example to .env.local and fill it in.",
    );
  }

  client = createClient(url, publishableKey, { auth: { persistSession: false } });
  return client;
}
