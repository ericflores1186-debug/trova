import type { Metadata } from "next";
import Image from "next/image";
import { notFound } from "next/navigation";
import { Play } from "lucide-react";

import { FlightCard } from "@/app/components/FlightCard";
import { HotelCard } from "@/app/components/HotelCard";
import { ShareButton } from "@/app/components/ShareButton";
import { Wordmark } from "@/app/components/Wordmark";
import { getStorefront } from "@/app/lib/storefronts";
import type { Storefront } from "@/app/lib/types";
import { detectPlatform } from "@/app/lib/video";
import { parseVideoId, thumbnailUrl } from "@/app/lib/youtube";

// A storefront is usually opened seconds after it is created, so serve it
// fresh rather than from a build-time cache.
export const dynamic = "force-dynamic";

type PageProps = {
  // Next.js 15 passes route params as a Promise.
  params: Promise<{ storefrontId: string }>;
};

/**
 * The video's picture. A YouTube thumbnail is derived from the video ID; a
 * TikTok or Instagram cover was copied into storage when the storefront was
 * built, because those platforms' own cover links expire.
 */
function coverFor(storefront: Storefront): { src: string; vertical: boolean } | null {
  const platform = detectPlatform(storefront.video_url);
  if (platform === "tiktok" || platform === "instagram") {
    return storefront.thumbnail_url ? { src: storefront.thumbnail_url, vertical: true } : null;
  }
  const videoId = parseVideoId(storefront.video_url);
  return videoId ? { src: thumbnailUrl(videoId), vertical: false } : null;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { storefrontId } = await params;
  const storefront = await getStorefront(storefrontId);

  if (!storefront) {
    return { title: "Storefront not found" };
  }

  const stays = storefront.affiliate_links.length;
  const trips = (storefront.flight_links ?? []).length;
  const parts = [
    stays > 0 ? `${stays} ${stays === 1 ? "stay" : "stays"}` : null,
    trips > 0 ? `${trips} ${trips === 1 ? "destination" : "destinations"}` : null,
  ].filter(Boolean);
  const description = `${parts.join(" and ")} from "${storefront.video_title}" — book them all in one place.`;
  const cover = coverFor(storefront);

  return {
    title: storefront.video_title,
    description,
    openGraph: {
      title: `${storefront.video_title} · Trova`,
      description,
      type: "website",
      images: cover ? [{ url: cover.src }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: `${storefront.video_title} · Trova`,
      description,
    },
  };
}

export default async function StorefrontPage({ params }: PageProps) {
  const { storefrontId } = await params;
  const storefront = await getStorefront(storefrontId);

  if (!storefront) notFound();

  const links = storefront.affiliate_links;
  const flights = storefront.flight_links ?? [];
  const cover = coverFor(storefront);
  const hasVideo = detectPlatform(storefront.video_url) !== null;

  return (
    <main className="relative">
      <div className="grain absolute inset-x-0 top-0 h-[420px]" aria-hidden />

      <div className="relative mx-auto max-w-5xl px-6 pb-24 pt-10">
        <header className="flex items-center justify-between gap-4">
          <Wordmark size="sm" />
          <ShareButton />
        </header>

        {/* --- Video header ------------------------------------------------ */}
        <section
          className={`rise mt-14 grid gap-10 lg:items-center ${
            cover?.vertical ? "lg:grid-cols-[1fr_auto]" : "lg:grid-cols-[1.15fr_1fr]"
          }`}
        >
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-clay">
              Stays from this video
            </p>
            <h1 className="mt-4 font-display text-4xl leading-[1.12] tracking-tight text-ink sm:text-5xl">
              {storefront.video_title}
            </h1>
            <p className="mt-5 text-base text-ink-soft">
              {links.length > 0 && (
                <>
                  {links.length} {links.length === 1 ? "place" : "places"} to stay
                </>
              )}
              {links.length > 0 && flights.length > 0 && " and "}
              {flights.length > 0 && (
                <>
                  {flights.length} {flights.length === 1 ? "destination" : "destinations"}
                </>
              )}
              , pulled straight from the video.
            </p>

            {hasVideo && (
              <a
                href={storefront.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-ink-soft underline decoration-sand-deep underline-offset-4 transition-colors hover:text-clay hover:decoration-clay"
              >
                <Play className="size-4" aria-hidden />
                Watch the original video
              </a>
            )}
          </div>

          {cover && (
            <a
              href={storefront.video_url}
              target="_blank"
              rel="noopener noreferrer"
              className={`group relative block overflow-hidden rounded-card border border-sand bg-sand ${
                // A vertical cover at full column width would be taller than
                // the screen, so it is sized like a phone instead.
                cover.vertical
                  ? "aspect-[9/16] w-44 justify-self-center sm:w-52 lg:w-60"
                  : "aspect-video"
              }`}
            >
              <Image
                src={cover.src}
                alt=""
                fill
                sizes={cover.vertical ? "240px" : "(max-width: 1024px) 100vw, 480px"}
                className="object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                priority
              />
              <span className="absolute inset-0 flex items-center justify-center bg-ink/15 transition-colors group-hover:bg-ink/25">
                <span className="flex size-14 items-center justify-center rounded-full bg-paper-raised/95 shadow-lg transition-transform group-hover:scale-105">
                  <Play className="ml-0.5 size-5 fill-ink text-ink" aria-hidden />
                </span>
              </span>
            </a>
          )}
        </section>

        {/* --- Hotel cards -------------------------------------------------- */}
        {links.length > 0 && (
          <section className="mt-20" aria-labelledby="stays">
            <h2
              id="stays"
              className="text-xs font-medium uppercase tracking-[0.18em] text-ink-faint"
            >
              Where to stay
            </h2>
            <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {links.map((link, index) => (
                <HotelCard
                  key={link.id}
                  link={link}
                  index={index}
                  storefrontId={storefront.id}
                />
              ))}
            </div>
          </section>
        )}

        {flights.length > 0 && (
          <section className="mt-16" aria-labelledby="getting-there">
            <h2
              id="getting-there"
              className="text-xs font-medium uppercase tracking-[0.18em] text-ink-faint"
            >
              Getting there
            </h2>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {flights.map((flight) => (
                <FlightCard key={flight.id} link={flight} storefrontId={storefront.id} />
              ))}
            </div>
          </section>
        )}

        {links.length === 0 && flights.length === 0 && (
          <section className="mt-20">
            <p className="rounded-card border border-dashed border-sand-deep p-10 text-center text-sm text-ink-faint">
              Nothing bookable was saved for this storefront.
            </p>
          </section>
        )}

        {/* --- Footer / disclosure ------------------------------------------ */}
        <footer className="mt-24 border-t border-sand pt-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <p className="max-w-md text-xs leading-relaxed text-ink-faint">
              Booking links on this page are affiliate links. The creator may earn a
              commission if you book, at no extra cost to you. Prices and availability
              are set by the booking provider.
            </p>
            <div className="flex shrink-0 items-center gap-2">
              <span className="text-xs text-ink-faint">Built with</span>
              <Wordmark size="sm" href="/" />
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}
