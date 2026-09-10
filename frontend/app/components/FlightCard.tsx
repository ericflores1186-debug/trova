import { ArrowRight, ArrowUpRight, Plane } from "lucide-react";

import type { FlightLink } from "@/app/lib/types";

/**
 * Deliberately lighter than HotelCard: flights are the supporting act on a
 * storefront that has hotels, and only carry the page when it has none.
 */
export function FlightCard({ link }: { link: FlightLink }) {
  const destination = link.destination_country
    ? `${link.destination_city}, ${link.destination_country}`
    : link.destination_city;

  return (
    <article className="group flex items-center gap-4 rounded-card border border-sand bg-paper-raised p-5 transition-all duration-300 hover:border-sand-deep hover:shadow-[0_12px_32px_-20px_rgb(25_21_18/0.25)]">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-clay-wash">
        <Plane className="size-4 text-clay-deep" aria-hidden />
      </span>

      <div className="min-w-0 flex-1">
        <h3 className="flex flex-wrap items-center gap-1.5 font-display text-xl leading-tight text-ink">
          {link.origin_city && (
            <>
              <span className="text-ink-faint">{link.origin_city}</span>
              <ArrowRight className="size-4 shrink-0 text-ink-faint" aria-hidden />
            </>
          )}
          {destination}
        </h3>
        {link.airline && (
          <p className="mt-1 text-sm text-ink-soft">Flew {link.airline}</p>
        )}
      </div>

      <a
        href={link.booking_url}
        target="_blank"
        /* `sponsored` is the correct rel for paid/affiliate outbound links. */
        rel="sponsored noopener noreferrer"
        className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-clay/30 px-4 py-2.5 text-sm font-medium text-clay-deep transition-colors hover:bg-clay hover:text-paper-raised focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-clay-deep"
      >
        Find flights
        <ArrowUpRight
          className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          aria-hidden
        />
        <span className="sr-only"> to {destination} (opens in a new tab)</span>
      </a>
    </article>
  );
}
