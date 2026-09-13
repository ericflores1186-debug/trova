import { Clapperboard, Hotel, Wand2 } from "lucide-react";

import { MyStorefronts } from "@/app/components/MyStorefronts";
import { StorefrontForm } from "@/app/components/StorefrontForm";
import { Wordmark } from "@/app/components/Wordmark";

// Nothing on this page is user-specific server-side: the storefront list is
// read from localStorage in the browser, so this can be statically rendered.

const HOW_IT_WORKS = [
  {
    icon: Clapperboard,
    title: "Paste a video",
    body: "A TikTok, or a YouTube video with captions turned on — a hotel tour, a room review, a city guide.",
  },
  {
    icon: Wand2,
    title: "Trova listens",
    body: "It reads what you said — and on TikTok, your caption, on-screen text and tagged location — and pulls out every stay you named.",
  },
  {
    icon: Hotel,
    title: "Share the page",
    body: "You get a clean storefront with a booking link for each stay. One link in your bio.",
  },
];

export default function DashboardPage() {

  return (
    <main className="relative">
      {/* --- Hero ------------------------------------------------------- */}
      <div className="grain absolute inset-x-0 top-0 h-[520px]" aria-hidden />

      <div className="relative mx-auto max-w-3xl px-6 pb-24 pt-10 sm:pt-16">
        <header className="flex items-center justify-between">
          <Wordmark size="sm" href={null} />
          <span className="rounded-full border border-sand bg-paper-raised px-3 py-1 text-xs text-ink-faint">
            Creator beta
          </span>
        </header>

        <section className="rise pt-16 sm:pt-24">
          <h1 className="font-display text-4xl leading-[1.1] tracking-tight text-ink sm:text-6xl">
            Every hotel you mentioned,
            <br />
            <span className="text-clay">bookable in one link.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-soft">
            Trova watches your travel video, finds every stay you talked about, and
            turns them into a storefront you can drop in your bio.
          </p>

          <div className="mt-10">
            <StorefrontForm />
          </div>
        </section>

        {/* --- How it works ---------------------------------------------- */}
        <section className="mt-28" aria-labelledby="how-it-works">
          <h2
            id="how-it-works"
            className="text-xs font-medium uppercase tracking-[0.18em] text-ink-faint"
          >
            How it works
          </h2>
          <div className="mt-6 grid gap-6 sm:grid-cols-3">
            {HOW_IT_WORKS.map(({ icon: Icon, title, body }, index) => (
              <div key={title} className="flex flex-col gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-clay-wash">
                    <Icon className="size-4 text-clay-deep" aria-hidden />
                  </span>
                  <span
                    aria-hidden
                    className="font-display text-sm text-ink-faint tabular-nums"
                  >
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="font-display text-xl text-ink">{title}</h3>
                <p className="text-sm leading-relaxed text-ink-soft">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <MyStorefronts />

        <footer className="mt-24 border-t border-sand pt-8">
          <p className="text-xs leading-relaxed text-ink-faint">
            Trova storefronts contain affiliate links. Creators may earn a commission
            on bookings at no extra cost to the traveller.
          </p>
        </footer>
      </div>
    </main>
  );
}
