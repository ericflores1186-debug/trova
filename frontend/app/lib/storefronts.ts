import { getSupabase } from "./supabase";
import type { Storefront } from "./types";

const STOREFRONT_SELECT =
  "id, creator_id, video_url, video_title, created_at, marker_used, " +
  "affiliate_links(id, hotel_name, location, booking_url, created_at), " +
  "flight_links(id, destination_city, destination_country, destination_iata, origin_city, airline, booking_url, created_at)";

/**
 * Fetch one storefront with its hotel links, in a single joined query.
 * Returns null when the ID does not exist, so the caller can render notFound().
 */
export async function getStorefront(id: string): Promise<Storefront | null> {
  try {
    const { data, error } = await getSupabase()
      .from("storefronts")
      .select(STOREFRONT_SELECT)
      .eq("id", id)
      .maybeSingle();

    if (error) {
      // A non-UUID path segment reaches Postgres as a cast error, not a 404.
      console.error("Failed to load storefront", id, error.message);
      return null;
    }
    if (!data) return null;

    // supabase-js cannot infer the row shape from a select string built at
    // runtime, so assert it against our own type rather than fight the generic.
    const row = data as unknown as Storefront;

    const byCreated = (a: { created_at: string | null }, b: { created_at: string | null }) =>
      (a.created_at ?? "").localeCompare(b.created_at ?? "");

    return {
      ...row,
      affiliate_links: [...(row.affiliate_links ?? [])].sort(byCreated),
      flight_links: [...(row.flight_links ?? [])].sort(byCreated),
    };
  } catch (error) {
    console.error("Supabase unavailable", error);
    return null;
  }
}
