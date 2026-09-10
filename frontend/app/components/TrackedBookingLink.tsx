"use client";

import type { ReactNode } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * A booking link that reports its own click.
 *
 * `href` stays the real affiliate URL, so the click works even if the Trova
 * API is down, asleep, or blocked by an extension. The report is fired
 * alongside navigation with `keepalive`, which survives the page unloading.
 *
 * The tradeoff is deliberate: routing clicks through a redirect on our own
 * server would count every one, but would also put our uptime in front of the
 * creator's revenue. Undercounting is an acceptable price; a dead booking link
 * is not.
 */
export function TrackedBookingLink({
  href,
  storefrontId,
  linkId,
  linkType,
  className,
  children,
}: {
  href: string;
  storefrontId: string;
  linkId: string;
  linkType: "hotel" | "flight";
  className?: string;
  children: ReactNode;
}) {
  function report() {
    try {
      void fetch(`${API_URL}/api/clicks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storefront_id: storefrontId,
          link_id: linkId,
          link_type: linkType,
        }),
        keepalive: true,
      }).catch(() => {
        // Offline, blocked, or API down. The visitor still reaches the
        // booking site; we simply lose this one data point.
      });
    } catch {
      /* never let analytics break navigation */
    }
  }

  return (
    <a
      href={href}
      target="_blank"
      /* `sponsored` is the correct rel for paid/affiliate outbound links. */
      rel="sponsored noopener noreferrer"
      onClick={report}
      onAuxClick={report}
      className={className}
    >
      {children}
    </a>
  );
}
