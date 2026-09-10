"""Proxy diagnostic. Answers one question: can this machine read YouTube?

    python check_proxy.py            # test this machine
    python check_proxy.py --remote https://trova-api.onrender.com

Run it locally to check your proxy credentials work at all. Run it with
--remote to check whether your DEPLOYED backend can fetch transcripts, which
is the question that actually matters -- your home IP is not blocked, so a
local pass proves nothing about production.
"""

from __future__ import annotations

import sys

# A short, reliably-captioned video. Any failure here is about access, not
# about this particular video.
TEST_VIDEO = "8jPQjjsBbIc"

OK = "  [OK]  "
BAD = "  [!!]  "
WARN = "  [~~]  "


def check_remote(base_url: str) -> None:
    """Ask a deployed Trova whether it can reach YouTube."""
    import requests

    base_url = base_url.rstrip("/")
    print(f"\nTesting the DEPLOYED backend at {base_url}")
    print("=" * 60)

    try:
        health = requests.get(f"{base_url}/health", timeout=90)
        health.raise_for_status()
        print(f"{OK}Backend is awake")
    except Exception as exc:
        print(f"{BAD}Could not reach the backend: {exc}")
        sys.exit(1)

    print("  Generating a storefront (may take ~30s, or ~90s if it was asleep)...")
    try:
        response = requests.post(
            f"{base_url}/api/generate-storefront",
            json={"video_url": f"https://www.youtube.com/watch?v={TEST_VIDEO}"},
            timeout=300,
        )
    except Exception as exc:
        print(f"{BAD}Request failed: {exc}")
        sys.exit(1)

    if response.ok:
        print(f"{OK}YouTube let the server through. The proxy is working.")
        print("\n  Trova is fully operational in production.\n")
        return

    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    message = body.get("message", response.text[:200])

    if "blocking transcript requests" in message:
        print(f"{BAD}YouTube is still blocking the server.")
        print("\n  Either no proxy is configured, or it is a DATACENTER proxy.")
        print("  YouTube blocks datacenter IPs. You need a RESIDENTIAL plan.")
        print("  See DEPLOY.md section 3.5.\n")
    elif "even through the proxy" in message:
        print(f"{WARN}A proxy IS configured, but YouTube still refused.")
        print("\n  Almost certainly a datacenter proxy rather than residential.")
        print("  Check the plan type on your proxy provider.\n")
    elif "no usable transcript" in message:
        print(f"{WARN}Reached YouTube, but this video had no transcript.")
        print("  That means access is fine -- try a different video.\n")
    else:
        print(f"{BAD}{message}\n")
    sys.exit(1)


def check_local() -> None:
    """Test whatever proxy config this machine has."""
    sys.path.insert(0, ".")
    from dotenv import load_dotenv

    load_dotenv(".env")

    from app import config
    from app.errors import TranscriptUnavailable
    from app.services.transcript import _build_proxy_config, fetch_transcript

    print("\nTesting THIS machine")
    print("=" * 60)

    if config.HAS_PROXY:
        kind = "Webshare" if config.WEBSHARE_PROXY_USERNAME else "generic"
        print(f"{OK}Proxy configured ({kind})")
    else:
        print(f"{WARN}No proxy configured -- testing your own connection")
        print("        Your home IP is not blocked, so a pass here does NOT")
        print("        mean production will work. Use --remote for that.")

    print(f"  Fetching transcript for {TEST_VIDEO}...")
    try:
        text = fetch_transcript(TEST_VIDEO)
    except TranscriptUnavailable as exc:
        print(f"{BAD}{exc.message}")
        if config.HAS_PROXY:
            print("\n  The proxy credentials may be wrong, or the plan may be")
            print("  datacenter rather than residential.\n")
        sys.exit(1)

    print(f"{OK}Got {len(text):,} characters")
    if config.HAS_PROXY:
        print("\n  Proxy credentials work. Now confirm production with:")
        print("    python check_proxy.py --remote https://trova-api.onrender.com\n")
    else:
        print()


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--remote":
        if len(args) < 2:
            print("Usage: python check_proxy.py --remote https://your-api.onrender.com")
            sys.exit(1)
        check_remote(args[1])
    else:
        check_local()


if __name__ == "__main__":
    main()
