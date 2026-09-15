import type { ApiError, GenerateStorefrontResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class StorefrontRequestError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "StorefrontRequestError";
    this.code = code;
  }
}

export type GenerateInput = {
  videoUrl: string;
  creatorName?: string;
  creatorHandle?: string;
};

/**
 * POST /api/generate-storefront on the FastAPI backend.
 *
 * The backend returns `{ code, message }` on every failure and the messages
 * are already written for end users, so they are surfaced verbatim. Only
 * transport-level failures get a message invented here.
 */
export async function generateStorefront(
  input: GenerateInput,
  signal?: AbortSignal,
): Promise<GenerateStorefrontResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/api/generate-storefront`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_url: input.videoUrl,
        creator_name: input.creatorName || null,
        creator_handle: input.creatorHandle || null,
      }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new StorefrontRequestError(
      "network_error",
      "Could not reach the Trova server. Check that the backend is running, then try again.",
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null;
    throw new StorefrontRequestError(
      body?.code ?? "unknown_error",
      body?.message ?? "Something went wrong while building your storefront.",
    );
  }

  return (await response.json()) as GenerateStorefrontResponse;
}
