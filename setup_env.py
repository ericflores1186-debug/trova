"""Interactive .env writer. Run this instead of hand-editing files.

    python setup_env.py

Prompts for each value, validates it looks right, and writes both
backend/.env and frontend/.env.local. Press Enter to keep an existing value.
Nothing is printed in full, and nothing leaves your machine.
"""

from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_ENV = os.path.join(ROOT, "backend", ".env")
FRONTEND_ENV = os.path.join(ROOT, "frontend", ".env.local")


def read_existing(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def mask(value: str) -> str:
    if len(value) <= 14:
        return value[:4] + "..."
    return f"{value[:14]}...{value[-4:]} ({len(value)} chars)"


def is_placeholder(value: str) -> bool:
    return not value or "PASTE_" in value or "your-" in value


def ask(label: str, current: str, validate) -> str:
    """Prompt until the answer validates. Enter keeps a valid existing value."""
    while True:
        if not is_placeholder(current):
            print(f"\n{label}")
            print(f"  currently: {mask(current)}")
            answer = input("  press Enter to keep, or paste a new value: ").strip()
            if not answer:
                return current
        else:
            print(f"\n{label}")
            answer = input("  paste here: ").strip()

        # Strip quotes people copy along with the value.
        answer = answer.strip("'\"").strip()

        problem = validate(answer)
        if problem:
            print(f"  -> {problem}")
            current = ""
            continue
        print(f"  -> looks good: {mask(answer)}")
        return answer


def check_url(value: str) -> str | None:
    if not value:
        return "Cannot be empty."
    if not value.startswith("https://"):
        return "Should start with https://"
    if not re.match(r"^https://[a-z0-9]+\.supabase\.co/?$", value):
        return "Should look like https://abcdefghijklm.supabase.co (no path after it)."
    return None


def check_secret(value: str) -> str | None:
    if not value:
        return "Cannot be empty."
    if value.startswith("sb_publishable_"):
        return "That is the PUBLISHABLE key. The backend needs the SECRET key (sb_secret_...)."
    if not (value.startswith("sb_secret_") or value.startswith("eyJ")):
        return "Expected sb_secret_... (or a legacy service_role key starting with eyJ)."
    return None


def check_publishable(value: str) -> str | None:
    if not value:
        return "Cannot be empty."
    if value.startswith("sb_secret_"):
        return "That is the SECRET key -- it must never go in the frontend. Use sb_publishable_..."
    if not (value.startswith("sb_publishable_") or value.startswith("eyJ")):
        return "Expected sb_publishable_... (or a legacy anon key starting with eyJ)."
    return None


def check_anthropic(value: str) -> str | None:
    if not value:
        return "Cannot be empty."
    if not value.startswith("sk-ant-"):
        return "Anthropic keys start with sk-ant-. Get one at console.anthropic.com -> API keys."
    return None


def main() -> None:
    print("\n" + "=" * 58)
    print("  Trova environment setup")
    print("=" * 58)
    print("\n  Supabase keys:  Dashboard -> Settings -> API Keys")
    print("  Anthropic key:  console.anthropic.com -> API keys")

    backend = read_existing(BACKEND_ENV)
    frontend = read_existing(FRONTEND_ENV)

    url = ask(
        "1/4  Supabase Project URL",
        backend.get("SUPABASE_URL", ""),
        check_url,
    ).rstrip("/")

    secret = ask(
        "2/4  Supabase SECRET key  (click the eye icon to reveal it first)",
        backend.get("SUPABASE_SECRET_KEY", ""),
        check_secret,
    )

    publishable = ask(
        "3/4  Supabase PUBLISHABLE key",
        frontend.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", ""),
        check_publishable,
    )

    anthropic_key = ask(
        "4/4  Anthropic API key",
        backend.get("ANTHROPIC_API_KEY", ""),
        check_anthropic,
    )

    with open(BACKEND_ENV, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by setup_env.py. Server-side only -- never commit this file.\n"
            f"SUPABASE_URL={url}\n"
            f"SUPABASE_SECRET_KEY={secret}\n"
            f"ANTHROPIC_API_KEY={anthropic_key}\n"
            f"EXTRACTION_MODEL={backend.get('EXTRACTION_MODEL') or 'claude-haiku-4-5'}\n"
            "TRAVELPAYOUTS_MOCK=true\n"
            "TRAVELPAYOUTS_API_TOKEN=placeholder-travelpayouts-token\n"
            "TRAVELPAYOUTS_MARKER=000000\n"
            "CORS_ORIGINS=http://localhost:3000\n"
        )

    with open(FRONTEND_ENV, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by setup_env.py. These values ship to the browser.\n"
            f"NEXT_PUBLIC_SUPABASE_URL={url}\n"
            f"NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY={publishable}\n"
            "NEXT_PUBLIC_API_URL=http://localhost:8000\n"
            "NEXT_PUBLIC_SITE_URL=http://localhost:3000\n"
        )

    print("\n" + "=" * 58)
    print(f"  Wrote {BACKEND_ENV}")
    print(f"  Wrote {FRONTEND_ENV}")
    print("\n  Next:  cd backend  &&  python check_setup.py")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    main()
