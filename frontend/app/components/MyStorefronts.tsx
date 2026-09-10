"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, X } from "lucide-react";

import { forgetStorefront, readMyStorefronts, type MyStorefront } from "@/app/lib/myStorefronts";

/**
 * Storefronts created in this browser. Reads localStorage on mount, so it
 * renders nothing on the server and never leaks another creator's work.
 */
export function MyStorefronts() {
  const [rows, setRows] = useState<MyStorefront[] | null>(null);

  useEffect(() => {
    setRows(readMyStorefronts());
  }, []);

  // null = not read yet (server render / first paint), [] = genuinely empty.
  if (rows === null || rows.length === 0) return null;

  function handleForget(id: string) {
    forgetStorefront(id);
    setRows((current) => (current ?? []).filter((row) => row.id !== id));
  }

  return (
    <section className="mt-24" aria-labelledby="yours">
      <h2 id="yours" className="text-xs font-medium uppercase tracking-[0.18em] text-ink-faint">
        Your storefronts
      </h2>

      <ul className="mt-6 divide-y divide-sand border-y border-sand">
        {rows.map((row) => (
          <li key={row.id} className="group flex items-center gap-3">
            <Link
              href={`/${row.id}`}
              className="flex flex-1 items-center justify-between gap-4 py-4 transition-colors"
            >
              <span className="line-clamp-1 text-sm text-ink-soft transition-colors group-hover:text-clay">
                {row.title}
              </span>
              <ArrowUpRight
                className="size-4 shrink-0 text-ink-faint transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-clay"
                aria-hidden
              />
            </Link>
            <button
              type="button"
              onClick={() => handleForget(row.id)}
              aria-label={`Remove ${row.title} from this list`}
              title="Remove from this list"
              className="shrink-0 rounded-lg p-1.5 text-ink-faint opacity-0 transition-all hover:bg-sand hover:text-ink focus-visible:opacity-100 group-hover:opacity-100"
            >
              <X className="size-3.5" aria-hidden />
            </button>
          </li>
        ))}
      </ul>

      <p className="mt-3 text-xs text-ink-faint">
        Saved in this browser only. Removing one from this list does not delete the
        storefront &mdash; its link keeps working.
      </p>
    </section>
  );
}
