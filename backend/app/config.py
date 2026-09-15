"""Environment configuration.

Loaded once at import time. Values that the service genuinely cannot run
without fail fast here rather than at the first request.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and fill it in."
        )
    return value


def _first_set(*names: str) -> str:
    """Return the first of `names` that is set, else fail naming all of them."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(
        f"Set one of: {', '.join(names)}. "
        "Copy .env.example to .env and fill it in."
    )


# --- Supabase -------------------------------------------------------------
SUPABASE_URL = _required("SUPABASE_URL")

# Supabase is retiring the legacy `service_role` JWT in favour of a secret key
# (`sb_secret_...`). Either works today, so accept both variable names.
SUPABASE_SECRET_KEY = _first_set("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_KEY")

# --- Anthropic ------------------------------------------------------------
# Not read directly: the SDK resolves ANTHROPIC_API_KEY (or an `ant auth login`
# profile) from the environment itself. We only warn so a missing key surfaces
# at boot instead of as a 401 on the first extraction.
if not os.getenv("ANTHROPIC_API_KEY"):
    logger.warning(
        "ANTHROPIC_API_KEY is not set. Extraction will fail unless the "
        "Anthropic SDK can resolve credentials another way."
    )

EXTRACTION_MODEL = os.getenv("EXTRACTION_MODEL", "claude-haiku-4-5")

# Return canned hotels instead of calling Claude. Lets you exercise the rest of
# the pipeline (transcript -> links -> Supabase -> storefront page) before you
# have an Anthropic key. Never leave this on in production.
MOCK_EXTRACTION = os.getenv("MOCK_EXTRACTION", "false").lower() == "true"

# --- Stay22 (hotels) -----------------------------------------------------
# Hotel links go through Stay22's Allez links. The affiliate ID is public by
# design -- it appears in every link -- so it has a default rather than being
# a required secret.
STAY22_AID = os.getenv("STAY22_AID", "trova")

# --- Travelpayouts (flights) --------------------------------------------
TRAVELPAYOUTS_MOCK = os.getenv("TRAVELPAYOUTS_MOCK", "true").lower() == "true"
TRAVELPAYOUTS_API_TOKEN = os.getenv("TRAVELPAYOUTS_API_TOKEN", "placeholder-travelpayouts-token")

# The marker is your Travelpayouts affiliate ID. Without a real one every
# booking link still works but earns nobody anything -- so say so loudly
# rather than let it ship unnoticed.
TRAVELPAYOUTS_MARKER = os.getenv("TRAVELPAYOUTS_MARKER", "000000")
MARKER_IS_PLACEHOLDER = TRAVELPAYOUTS_MARKER in ("", "000000") or not TRAVELPAYOUTS_MARKER.isdigit()

if MARKER_IS_PLACEHOLDER:
    logger.warning(
        "TRAVELPAYOUTS_MARKER is %r -- booking links will work but NO commission "
        "will be attributed. Get your marker at travelpayouts.com -> Profile.",
        TRAVELPAYOUTS_MARKER,
    )

# --- YouTube transcript proxy --------------------------------------------
# YouTube blocks datacenter IP ranges, so transcript fetches fail from any
# cloud host (Render, Railway, Fly, AWS...) while working fine from a home
# connection. A residential proxy is the only reliable fix.
#
# Set EITHER the Webshare pair (recommended -- the library has built-in
# support including rotation and retries) OR a generic proxy URL.
WEBSHARE_PROXY_USERNAME = os.getenv("WEBSHARE_PROXY_USERNAME", "")
WEBSHARE_PROXY_PASSWORD = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
GENERIC_PROXY_HTTP_URL = os.getenv("GENERIC_PROXY_HTTP_URL", "")
GENERIC_PROXY_HTTPS_URL = os.getenv("GENERIC_PROXY_HTTPS_URL", "")

HAS_PROXY = bool(
    (WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD)
    or GENERIC_PROXY_HTTP_URL
    or GENERIC_PROXY_HTTPS_URL
)

# Commit this build was made from. Render injects RENDER_GIT_COMMIT; without
# it this is "unknown". Surfaced on /health so a deploy can be confirmed live
# before testing against it -- otherwise a test silently hits the old
# container and its result means nothing.
GIT_COMMIT = (
    os.getenv("RENDER_GIT_COMMIT")
    or os.getenv("GIT_COMMIT")
    or "unknown"
)[:12]

# --- App ------------------------------------------------------------------
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Transcripts longer than this are split into chunks and extracted per chunk,
# rather than truncated. ~120k chars is roughly 30k tokens, comfortably inside
# the extraction model's context window with room for the system prompt.
TRANSCRIPT_CHUNK_CHARS = int(os.getenv("TRANSCRIPT_CHUNK_CHARS", "120000"))
