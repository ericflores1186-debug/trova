import { parseVideoId } from "./youtube";

export type Platform = "youtube" | "tiktok" | "instagram";

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

// Mirrors backend/app/services/instagram.py: a post, Reel or IGTV link,
// optionally after the username, or an app share link.
const INSTAGRAM_POST = /^\/(?:(?!share\/)[\w.]+\/)?(?:reels?|p|tv)\/[\w-]{10,}(?:\/|$)/;
const INSTAGRAM_SHARE = /^\/share\/(?:\w+\/)?[\w-]+\/?$/;

/** True for an Instagram post or Reel link, including instagram.com/share links. */
export function isInstagramUrl(url: string): boolean {
  const parsed = parseUrl(url);
  if (!parsed) return false;

  const host = parsed.hostname.toLowerCase().replace(/^(www\.|m\.)/, "");
  if (host !== "instagram.com" && host !== "instagr.am") return false;

  return INSTAGRAM_POST.test(parsed.pathname) || INSTAGRAM_SHARE.test(parsed.pathname);
}

/** Which supported platform a video link belongs to, or null. */
export function detectPlatform(url: string): Platform | null {
  if (parseVideoId(url)) return "youtube";
  if (isTikTokUrl(url)) return "tiktok";
  if (isInstagramUrl(url)) return "instagram";
  return null;
}
