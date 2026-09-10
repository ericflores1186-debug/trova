/** Extract the 11-character video ID from a YouTube URL, or null. */
export function parseVideoId(url: string): string | null {
  const trimmed = (url ?? "").trim();
  if (!trimmed) return null;
  if (/^[A-Za-z0-9_-]{11}$/.test(trimmed)) return trimmed;

  let parsed: URL;
  try {
    parsed = new URL(trimmed.includes("://") ? trimmed : `https://${trimmed}`);
  } catch {
    return null;
  }

  const host = parsed.hostname.replace(/^(www\.|m\.)/, "");
  let id = "";

  if (host === "youtu.be") {
    id = parsed.pathname.split("/").filter(Boolean)[0] ?? "";
  } else if (host === "youtube.com" || host === "youtube-nocookie.com") {
    if (parsed.pathname === "/watch") {
      id = parsed.searchParams.get("v") ?? "";
    } else {
      const match = parsed.pathname.match(/^\/(?:shorts|embed|live|v)\/([^/]+)/);
      id = match?.[1] ?? "";
    }
  }

  return /^[A-Za-z0-9_-]{11}$/.test(id) ? id : null;
}

/** maxresdefault falls back to hqdefault automatically on YouTube's CDN. */
export function thumbnailUrl(videoId: string): string {
  return `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`;
}
