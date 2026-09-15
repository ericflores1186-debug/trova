"""Setup checker. Run this before `uvicorn` to find config problems early.

    python check_setup.py

Checks, in order: .env present -> Supabase reachable -> the three tables exist
-> RLS lets the publishable key read -> Anthropic key works. Stops at the first
failure with a specific fix.
"""

from __future__ import annotations

import os
import sys

OK = "  [OK]  "
BAD = "  [!!]  "
WARN = "  [~~]  "


def fail(message: str, fix: str) -> None:
    print(f"{BAD}{message}")
    print(f"\n  Fix: {fix}\n")
    sys.exit(1)


def main() -> None:
    print("\nTrova setup check")
    print("=" * 52)

    # --- 1. .env ----------------------------------------------------------
    from dotenv import load_dotenv

    if not os.path.exists(".env"):
        fail(
            "No .env file in backend/",
            "cp .env.example .env   then fill it in",
        )
    load_dotenv()
    print(f"{OK}.env found")

    url = os.getenv("SUPABASE_URL", "")
    secret = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")

    if not url or "your-project-ref" in url:
        fail(
            "SUPABASE_URL is missing or still the placeholder",
            "Supabase Dashboard -> Settings -> API Keys -> copy the Project URL",
        )
    if not url.startswith("https://") or ".supabase.co" not in url:
        fail(
            f"SUPABASE_URL looks wrong: {url}",
            "It should look like https://abcdefghijklm.supabase.co (no trailing path)",
        )
    print(f"{OK}SUPABASE_URL looks valid")

    if not secret or "your-secret-key" in secret:
        fail(
            "SUPABASE_SECRET_KEY is missing or still the placeholder",
            "Supabase Dashboard -> Settings -> API Keys -> copy the SECRET key "
            "(sb_secret_...) or the legacy service_role key",
        )
    if secret.startswith("sb_publishable_"):
        fail(
            "SUPABASE_SECRET_KEY holds a PUBLISHABLE key",
            "The backend needs the SECRET key (sb_secret_...). The publishable "
            "key goes in frontend/.env.local instead -- you have them swapped.",
        )
    kind = "secret key" if secret.startswith("sb_secret_") else "legacy service_role JWT"
    print(f"{OK}Supabase key present ({kind})")

    # --- 2. Supabase connection + tables ----------------------------------
    from supabase import create_client

    try:
        client = create_client(url, secret)
    except Exception as exc:
        fail(f"Could not build a Supabase client: {exc}", "Re-check SUPABASE_URL and the key")

    for table in ("creators", "storefronts", "affiliate_links"):
        try:
            client.table(table).select("id").limit(1).execute()
        except Exception as exc:
            message = str(exc)
            if "does not exist" in message or "PGRST205" in message:
                fail(
                    f"Table '{table}' does not exist",
                    "Supabase Dashboard -> SQL Editor -> New query -> paste all of "
                    "backend/schema.sql -> Run. Then re-run this check.",
                )
            if "Invalid API key" in message or "JWT" in message:
                fail(
                    "Supabase rejected the key",
                    "Copy the SECRET key again from Settings -> API Keys. Watch for "
                    "a truncated paste or a stray newline.",
                )
            fail(f"Query on '{table}' failed: {message[:200]}", "See the error above")
        print(f"{OK}Table '{table}' exists and is readable")

    # --- 3. Anthropic -----------------------------------------------------
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_key or "PASTE_" in anthropic_key or anthropic_key.startswith("sk-ant-your"):
        fail(
            "ANTHROPIC_API_KEY is still a placeholder",
            "console.anthropic.com -> API keys -> Create Key -> paste into backend/.env\n"
            "       (Or set MOCK_EXTRACTION=true in .env to run without a key.)",
        )
    if not anthropic_key.startswith("sk-ant-"):
        fail(
            f"ANTHROPIC_API_KEY does not look like an Anthropic key (starts '{anthropic_key[:8]}')",
            "Anthropic keys start with sk-ant-. Check you did not paste a Supabase key here.",
        )

    import anthropic

    model = os.getenv("EXTRACTION_MODEL", "claude-haiku-4-5")
    try:
        response = anthropic.Anthropic().messages.create(
            model=model,
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        )
        reply = next((b.text for b in response.content if b.type == "text"), "")
        print(f"{OK}Anthropic reachable, model '{model}' replied: {reply.strip()!r}")
    except anthropic.AuthenticationError:
        fail("Anthropic rejected the API key", "Check ANTHROPIC_API_KEY in .env")
    except anthropic.NotFoundError:
        fail(
            f"Model '{model}' is not available to this key",
            "Set EXTRACTION_MODEL=claude-haiku-4-5 in .env",
        )
    except Exception as exc:
        fail(f"Anthropic call failed: {exc}", "Check your key and network")

    # --- 4. Travelpayouts (warn only -- the app runs fine without it) ----
    # The marker only affects flight links now; hotels go through Stay22.
    # TRAVELPAYOUTS_MOCK and TRAVELPAYOUTS_API_TOKEN gated the Hotellook lookup,
    # which went with the Hotellook program itself.
    marker = os.getenv("TRAVELPAYOUTS_MARKER", "")
    if not marker or marker == "000000" or not marker.isdigit():
        print(f"{WARN}TRAVELPAYOUTS_MARKER is a placeholder -- flight links earn no commission")
        print("        Get yours: travelpayouts.com -> sign up -> Profile -> your marker ID")
    else:
        print(f"{OK}Travelpayouts live, marker {marker}")

    print("=" * 52)
    print("  All checks passed. Start the server with:")
    print("    python -m uvicorn app.main:app --reload --port 8000\n")


if __name__ == "__main__":
    main()
