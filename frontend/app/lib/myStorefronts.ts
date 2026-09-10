"use client";

/**
 * Per-browser record of storefronts created here.
 *
 * Trova has no accounts yet, so there is no server-side notion of "mine".
 * Until there is, the dashboard lists what this browser made rather than
 * everything in the database -- a creator must never see another creator's
 * storefronts just by loading the homepage.
 *
 * Storefront pages stay public by URL. That is the product. It is the
 * *listing* that must not be global.
 */

const KEY = "trova.my-storefronts.v1";
const LIMIT = 24;

export type MyStorefront = {
  id: string;
  title: string;
  createdAt: string;
};

function isRecord(value: unknown): value is MyStorefront {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return typeof row.id === "string" && typeof row.title === "string";
}

export function readMyStorefronts(): MyStorefront[] {
  // Private windows, cleared site data, and storage-blocking settings all
  // throw here rather than returning empty.
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isRecord);
  } catch {
    return [];
  }
}

export function rememberStorefront(entry: Omit<MyStorefront, "createdAt">): void {
  try {
    const existing = readMyStorefronts().filter((row) => row.id !== entry.id);
    const next = [{ ...entry, createdAt: new Date().toISOString() }, ...existing].slice(0, LIMIT);
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Not being able to remember is a lost convenience, never an error the
    // creator should see -- their storefront was still created.
  }
}

export function forgetStorefront(id: string): void {
  try {
    const next = readMyStorefronts().filter((row) => row.id !== id);
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* see above */
  }
}
