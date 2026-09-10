"""Travelpayouts SubIDs.

Every booking link carries Trova's marker plus a SubID identifying the
creator: `marker=572600.wanderlust`. Travelpayouts pays Trova and its
Performance report splits earnings by SubID, which is how each creator's
share is worked out.

Travelpayouts allows Latin letters, digits and underscores in a SubID, up to
4096 characters. Their guidance is to keep them short and meaningful -- and
since these get reconciled by hand each month, readable beats clever.
"""

from __future__ import annotations

import re
import uuid

_ALLOWED = re.compile(r"[^a-z0-9_]+")
MAX_LENGTH = 40


def slugify(value: str) -> str:
    """Reduce a handle or name to a legal SubID fragment."""
    cleaned = _ALLOWED.sub("_", (value or "").strip().casefold())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:MAX_LENGTH]


def build(handle: str | None, name: str | None, creator_id: str | None = None) -> str:
    """Return a readable SubID, falling back to something guaranteed unique.

    A handle is preferred because it makes the monthly Travelpayouts report
    legible: "wanderlust" is reconcilable at a glance, "c_a3f9c2b1" is not.
    """
    for candidate in (handle, name):
        slug = slugify(candidate or "")
        if slug:
            return slug

    suffix = (creator_id or uuid.uuid4().hex).replace("-", "")[:8]
    return f"c_{suffix}"


def disambiguate(subid: str, attempt: int) -> str:
    """Append a counter when a SubID is already taken.

    Sanitising can collide -- "@a.b" and "@a-b" both reduce to "a_b" -- and two
    creators sharing a SubID would merge their earnings in the report.
    """
    suffix = f"_{attempt}"
    return f"{subid[: MAX_LENGTH - len(suffix)]}{suffix}"
