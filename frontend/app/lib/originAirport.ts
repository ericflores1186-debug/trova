"use client";

/**
 * The visitor's nearest airport, for building Aviasales deeplinks.
 *
 * Aviasales `params` are origin-first: "NYCCHC1" means New York to
 * Christchurch. Origin is the *visitor's* home airport, so it cannot be known
 * when the storefront is created -- only in the browser that opens it.
 *
 * Travelpayouts exposes a geolocation endpoint for exactly this. Resolved once
 * per session and cached; every failure degrades to "no origin", which still
 * produces a usable link.
 */

const WHEREAMI = "https://www.travelpayouts.com/whereami?locale=en";
const CACHE_KEY = "trova.origin-iata.v1";

let inFlight: Promise<string | null> | null = null;

function readCache(): string | null {
  try {
    return window.sessionStorage.getItem(CACHE_KEY);
  } catch {
    return null;
  }
}

function writeCache(iata: string): void {
  try {
    window.sessionStorage.setItem(CACHE_KEY, iata);
  } catch {
    /* private mode, blocked storage -- we just re-fetch next time */
  }
}

export async function getOriginIata(): Promise<string | null> {
  const cached = readCache();
  if (cached) return cached;

  // One request per page even when several cards mount at once.
  if (inFlight) return inFlight;

  inFlight = (async () => {
    try {
      const response = await fetch(WHEREAMI, { signal: AbortSignal.timeout(4000) });
      if (!response.ok) return null;
      const data: unknown = await response.json();
      const iata = (data as { iata?: unknown })?.iata;
      if (typeof iata === "string" && /^[A-Za-z]{3}$/.test(iata)) {
        const code = iata.toUpperCase();
        writeCache(code);
        return code;
      }
      return null;
    } catch {
      // Offline, blocked by an extension, or slow. Not worth retrying.
      return null;
    } finally {
      inFlight = null;
    }
  })();

  return inFlight;
}

/**
 * Rewrite a flight booking URL to start from the visitor's own airport.
 *
 * Returns the original URL unchanged if anything is missing, so a caller can
 * use the result unconditionally.
 */
export function withOrigin(
  bookingUrl: string,
  destinationIata: string | null,
  originIata: string | null,
): string {
  if (!destinationIata || !originIata || originIata === destinationIata) {
    return bookingUrl;
  }
  try {
    const url = new URL(bookingUrl);
    // Trailing 1 = one adult. Aviasales rejects the link without it.
    url.searchParams.set("params", `${originIata}${destinationIata}1`.toUpperCase());
    return url.toString();
  } catch {
    return bookingUrl;
  }
}
