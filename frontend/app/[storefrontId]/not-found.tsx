import Link from "next/link";
import { ArrowLeft, Compass } from "lucide-react";

import { Wordmark } from "@/app/components/Wordmark";

export default function StorefrontNotFound() {
  return (
    <main className="relative">
      <div className="grain absolute inset-x-0 top-0 h-[420px]" aria-hidden />

      <div className="relative mx-auto flex min-h-dvh max-w-xl flex-col px-6 py-10">
        <Wordmark size="sm" />

        <div className="flex flex-1 flex-col items-start justify-center gap-6 pb-24">
          <span className="flex size-12 items-center justify-center rounded-xl bg-clay-wash">
            <Compass className="size-5 text-clay-deep" aria-hidden />
          </span>

          <h1 className="font-display text-4xl leading-tight tracking-tight text-ink sm:text-5xl">
            This storefront has wandered off.
          </h1>
          <p className="text-base leading-relaxed text-ink-soft">
            The link may be mistyped, or the storefront may have been removed. Build a
            new one from any travel video with captions.
          </p>

          <Link
            href="/"
            className="group inline-flex items-center gap-2 rounded-xl bg-clay px-5 py-3 text-sm font-medium text-paper-raised transition-colors hover:bg-clay-deep"
          >
            <ArrowLeft
              className="size-4 transition-transform group-hover:-translate-x-0.5"
              aria-hidden
            />
            Back to Trova
          </Link>
        </div>
      </div>
    </main>
  );
}
