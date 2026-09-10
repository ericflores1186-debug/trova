"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  Check,
  Loader2,
  Sparkles,
  Youtube,
} from "lucide-react";

import { generateStorefront, StorefrontRequestError } from "@/app/lib/api";
import { rememberStorefront } from "@/app/lib/myStorefronts";
import { parseVideoId } from "@/app/lib/youtube";

/**
 * The backend runs transcript -> extraction -> links -> save as one request,
 * so there is no server-sent progress to subscribe to. These steps advance on
 * elapsed time as an honest estimate of where the job is; the final step holds
 * until the response actually lands.
 */
const STEPS = [
  { label: "Pulling the transcript", after: 0 },
  { label: "Finding every stay you mentioned", after: 3500 },
  { label: "Matching booking links", after: 12000 },
  { label: "Building your storefront", after: 17000 },
] as const;

export function StorefrontForm() {
  const router = useRouter();
  const [videoUrl, setVideoUrl] = useState("");
  const [creatorName, setCreatorName] = useState("");
  const [youtubeHandle, setYoutubeHandle] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Advance the progress stepper while a request is in flight.
  useEffect(() => {
    if (!isPending) {
      setStep(0);
      return;
    }
    const timers = STEPS.map((s, index) =>
      s.after === 0 ? null : setTimeout(() => setStep(index), s.after),
    );
    return () => timers.forEach((t) => t && clearTimeout(t));
  }, [isPending]);

  // Abandon an in-flight request if the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const trimmedUrl = videoUrl.trim();
  const looksValid = trimmedUrl.length > 0 && parseVideoId(trimmedUrl) !== null;
  const showFormatHint = trimmedUrl.length > 6 && !looksValid;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (isPending || !looksValid) return;

    setError(null);
    setIsPending(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const result = await generateStorefront(
        {
          videoUrl: trimmedUrl,
          creatorName: creatorName.trim(),
          youtubeHandle: youtubeHandle.trim(),
        },
        controller.signal,
      );
      // No accounts yet, so "mine" lives in this browser.
      rememberStorefront({ id: result.storefront_id, title: result.video_title });
      // Keep the spinner up through navigation -- the storefront is a server
      // component, so there is a beat before the new page paints.
      router.push(`/${result.storefront_id}`);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setIsPending(false);
      setError(
        err instanceof StorefrontRequestError
          ? { code: err.code, message: err.message }
          : { code: "unknown_error", message: "Something went wrong. Please try again." },
      );
    }
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="rounded-card border border-sand bg-paper-raised p-2 shadow-[0_1px_2px_rgb(25_21_18/0.04),0_12px_32px_-12px_rgb(25_21_18/0.12)]">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="flex flex-1 items-center gap-3 px-3 py-2">
              <Youtube className="size-5 shrink-0 text-ink-faint" aria-hidden />
              <input
                type="text"
                inputMode="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                disabled={isPending}
                placeholder="Paste a YouTube video link"
                aria-label="YouTube video URL"
                aria-invalid={showFormatHint}
                className="w-full bg-transparent text-base text-ink outline-none placeholder:text-ink-faint disabled:opacity-60"
              />
            </div>

            <button
              type="submit"
              disabled={!looksValid || isPending}
              className="group inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-clay px-5 py-3 text-sm font-medium text-paper-raised transition-all hover:bg-clay-deep disabled:cursor-not-allowed disabled:bg-sand-deep disabled:text-ink-faint"
            >
              {isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  Working
                </>
              ) : (
                <>
                  <Sparkles className="size-4" aria-hidden />
                  Build storefront
                  <ArrowRight
                    className="size-4 transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </>
              )}
            </button>
          </div>
        </div>

        {showFormatHint && (
          <p className="px-1 text-sm text-ink-faint">
            That doesn&apos;t look like a YouTube link yet &mdash; try
            youtube.com/watch?v=&hellip; or youtu.be/&hellip;
          </p>
        )}

        <details className="group px-1">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 text-sm text-ink-faint transition-colors hover:text-ink-soft">
            <span className="transition-transform group-open:rotate-90">&rsaquo;</span>
            Add your creator details
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <input
              type="text"
              value={creatorName}
              onChange={(e) => setCreatorName(e.target.value)}
              disabled={isPending}
              placeholder="Channel name"
              aria-label="Channel name"
              className="rounded-xl border border-sand bg-paper-raised px-4 py-2.5 text-sm text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-clay disabled:opacity-60"
            />
            <input
              type="text"
              value={youtubeHandle}
              onChange={(e) => setYoutubeHandle(e.target.value)}
              disabled={isPending}
              placeholder="@handle"
              aria-label="YouTube handle"
              className="rounded-xl border border-sand bg-paper-raised px-4 py-2.5 text-sm text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-clay disabled:opacity-60"
            />
          </div>
          <p className="mt-2 text-xs text-ink-faint">
            Optional. Adding a handle groups every storefront you make under one creator.
          </p>
        </details>
      </form>

      {isPending && <ProgressPanel step={step} />}

      {error && (
        <div
          role="alert"
          className="rise mt-4 flex gap-3 rounded-card border border-clay/25 bg-clay-wash p-4"
        >
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-clay-deep" aria-hidden />
          <div className="space-y-1">
            <p className="text-sm leading-relaxed text-ink">{error.message}</p>
            {error.code === "transcript_unavailable" && (
              <p className="text-xs text-ink-faint">
                Trova reads what you said out loud, so the video needs captions turned on.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ProgressPanel({ step }: { step: number }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rise mt-4 rounded-card border border-sand bg-paper-raised p-5"
    >
      <ol className="space-y-3">
        {STEPS.map((s, index) => {
          const done = index < step;
          const active = index === step;
          return (
            <li key={s.label} className="flex items-center gap-3">
              <span
                className={`flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                  done
                    ? "border-moss bg-moss text-paper-raised"
                    : active
                      ? "border-clay text-clay"
                      : "border-sand-deep text-transparent"
                }`}
              >
                {done ? (
                  <Check className="size-3" aria-hidden />
                ) : active ? (
                  <Loader2 className="size-3 animate-spin" aria-hidden />
                ) : null}
              </span>
              <span
                className={`text-sm transition-colors ${
                  done ? "text-ink-soft" : active ? "text-ink" : "text-ink-faint"
                }`}
              >
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 border-t border-sand pt-3 text-xs text-ink-faint">
        Longer videos take longer &mdash; a 30-minute vlog is usually done in under a minute.
      </p>
    </div>
  );
}
