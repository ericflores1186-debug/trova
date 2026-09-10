import { ArrowUpRight, MapPin } from "lucide-react";

import type { AffiliateLink } from "@/app/lib/types";

export function HotelCard({ link, index }: { link: AffiliateLink; index: number }) {
  const hasLocation = link.location && link.location !== "Unknown";

  return (
    <article className="group flex flex-col overflow-hidden rounded-card border border-sand bg-paper-raised transition-all duration-300 hover:-translate-y-0.5 hover:border-sand-deep hover:shadow-[0_16px_40px_-20px_rgb(25_21_18/0.25)]">
      <div className="flex flex-1 flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-4">
          <h3 className="font-display text-2xl leading-tight text-ink">
            {link.hotel_name}
          </h3>
          <span
            aria-hidden
            className="mt-1 shrink-0 font-display text-sm text-ink-faint tabular-nums"
          >
            {String(index + 1).padStart(2, "0")}
          </span>
        </div>

        <p className="flex items-center gap-1.5 text-sm text-ink-soft">
          <MapPin className="size-4 shrink-0 text-clay" aria-hidden />
          {hasLocation ? (
            link.location
          ) : (
            <span className="text-ink-faint">Location not mentioned</span>
          )}
        </p>

        <div className="mt-auto pt-2">
          <a
            href={link.booking_url}
            target="_blank"
            /* `sponsored` is the correct rel for paid/affiliate outbound links. */
            rel="sponsored noopener noreferrer"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-clay px-5 py-3 text-sm font-medium text-paper-raised transition-colors hover:bg-clay-deep focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-clay-deep"
          >
            Book now
            <ArrowUpRight
              className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              aria-hidden
            />
            <span className="sr-only">
              {" "}
              at {link.hotel_name}
              {hasLocation ? `, ${link.location}` : ""} (opens in a new tab)
            </span>
          </a>
        </div>
      </div>
    </article>
  );
}
