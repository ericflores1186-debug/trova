"use client";

import { useEffect, useState } from "react";
import { Check, Link2 } from "lucide-react";

/**
 * Copies the storefront's own URL. Falls back to the Web Share sheet on
 * devices that have one, and to a manual prompt where the clipboard API is
 * unavailable (non-HTTPS origins, older browsers).
 */
export function ShareButton() {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  async function handleShare() {
    const url = window.location.href;

    if (navigator.share) {
      try {
        await navigator.share({ title: document.title, url });
        return;
      } catch {
        // User dismissed the sheet, or sharing is blocked -- fall through.
      }
    }

    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      window.prompt("Copy this link:", url);
    }
  }

  return (
    <button
      type="button"
      onClick={handleShare}
      className="inline-flex items-center gap-2 rounded-xl border border-sand bg-paper-raised px-4 py-2.5 text-sm font-medium text-ink-soft transition-colors hover:border-sand-deep hover:text-ink"
    >
      {copied ? (
        <>
          <Check className="size-4 text-moss" aria-hidden />
          Link copied
        </>
      ) : (
        <>
          <Link2 className="size-4" aria-hidden />
          Share
        </>
      )}
    </button>
  );
}
