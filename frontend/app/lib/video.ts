import { parseVideoId } from "./youtube";

export type Platform = "youtube" | "tiktok";

// Mirrors backend/app/services/tiktok.py, which has the final say: this only
// decides whether a pasted link is worth sending.
const TIKTOK_POST = /^\/@[\w.-]*\/(?:video|photo)\/\d{15,21}(?:\/|$)/;
const TIKTOK_ID_ONLY = /^\/(?:v\/\d{15,21}(?:\.html)?|embed(?:\/v2)?\/\d{15,21}|player\/v1\/\d{15,21})\/?$/;
const TIKTOK_SHARE_PATH = /^\/t\/[\w-]+\/?$/;

function parseUrl(url: string): URL | null {
  const trimmed = (url ?? "").trim();
  if (!trimmed) return null;
  try {
    return new URL(trimmed.includes("://") ? trimmed : `https://${trimmed}`);
  } catch {
    return null;
  }
}

/** True for a TikTok post link, including vm.tiktok.com share links. */
export function isTikTokUrl(url: string): boolean {
  const parsed = parseUrl(url);
  if (!parsed) return false;

  const host = parsed.hostname.toLowerCase().replace(/^(www\.|m\.)/, "");
  if (host === "vm.tiktok.com" || host === "vt.tiktok.com") {
    return /^\/[\w-]+\/?$/.test(parsed.pathname);
  }
  if (host !== "tiktok.com") return false;

  return [TIKTOK_POST, TIKTOK_ID_ONLY, TIKTOK_SHARE_PATH].some((pattern) =>
    pattern.test(parsed.pathname),
  );
}

/** Which supported platform a video link belongs to, or null. */
export function detectPlatform(url: string): Platform | null {
  if (parseVideoId(url)) return "youtube";
  if (isTikTokUrl(url)) return "tiktok";
  return null;
}
