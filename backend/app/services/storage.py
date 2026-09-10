"""Supabase persistence for creators, storefronts, and affiliate links."""

from __future__ import annotations

import logging

from postgrest.exceptions import APIError

from app.db import get_client
from app.errors import StorageFailed, StorefrontNotFound
from app.models.schemas import (
    AffiliateLinkOut,
    FlightLinkOut,
    FlightWithLink,
    HotelWithLink,
    StorefrontOut,
)

logger = logging.getLogger(__name__)


def upsert_creator(
    name: str | None,
    youtube_handle: str | None,
    travelpayouts_marker: str | None = None,
) -> dict:
    """Return the creator row, reusing an existing one when the handle matches.

    A supplied marker updates the stored one; omitting it keeps whatever the
    creator already had, so a later storefront does not silently stop paying
    them just because the field was left blank.
    """
    client = get_client()
    handle = (youtube_handle or "").strip() or None
    display_name = (name or "").strip() or handle or "Unknown creator"
    marker = (travelpayouts_marker or "").strip() or None

    try:
        if handle:
            existing = (
                client.table("creators")
                .select("id, name, youtube_handle, travelpayouts_marker")
                .eq("youtube_handle", handle)
                .limit(1)
                .execute()
            )
            if existing.data:
                row = existing.data[0]
                if marker and marker != row.get("travelpayouts_marker"):
                    updated = (
                        client.table("creators")
                        .update({"travelpayouts_marker": marker})
                        .eq("id", row["id"])
                        .execute()
                    )
                    logger.info("Updated marker for creator %s", row["id"])
                    return updated.data[0] if updated.data else {**row, "travelpayouts_marker": marker}
                return row

        created = (
            client.table("creators")
            .insert(
                {
                    "name": display_name,
                    "youtube_handle": handle,
                    "travelpayouts_marker": marker,
                }
            )
            .execute()
        )
    except APIError as exc:
        logger.exception("Creator upsert failed")
        if "travelpayouts_marker" in str(exc):
            raise StorageFailed(
                "The creators table has no travelpayouts_marker column. Run "
                "backend/schema_creator_marker.sql in the Supabase SQL editor."
            ) from exc
        raise StorageFailed(f"Could not save the creator: {exc.message}") from exc

    if not created.data:
        raise StorageFailed("Could not save the creator.")

    return created.data[0]


def create_storefront(
    creator_id: str, video_url: str, video_title: str, marker_used: str
) -> str:
    client = get_client()
    try:
        created = (
            client.table("storefronts")
            .insert(
                {
                    "creator_id": creator_id,
                    "video_url": video_url,
                    "video_title": video_title,
                    "marker_used": marker_used,
                }
            )
            .execute()
        )
    except APIError as exc:
        logger.exception("Storefront insert failed")
        raise StorageFailed(f"Could not save the storefront: {exc.message}") from exc

    if not created.data:
        raise StorageFailed("Could not save the storefront.")

    return created.data[0]["id"]


def create_affiliate_links(storefront_id: str, hotels: list[HotelWithLink]) -> list[AffiliateLinkOut]:
    """Insert all links in one batch and return them in insertion order."""
    if not hotels:
        return []

    rows = [
        {
            "storefront_id": storefront_id,
            "hotel_name": hotel.hotel_name,
            "location": hotel.location,
            "booking_url": hotel.booking_url,
        }
        for hotel in hotels
    ]

    client = get_client()
    try:
        created = client.table("affiliate_links").insert(rows).execute()
    except APIError as exc:
        logger.exception("Affiliate link insert failed")
        raise StorageFailed(f"Could not save the hotel links: {exc.message}") from exc

    return [AffiliateLinkOut(**row) for row in created.data]


def create_flight_links(storefront_id: str, flights: list[FlightWithLink]) -> list[FlightLinkOut]:
    """Insert all flight links in one batch and return them in insertion order."""
    if not flights:
        return []

    rows = [
        {
            "storefront_id": storefront_id,
            "destination_city": flight.destination_city,
            "destination_country": flight.destination_country,
            "origin_city": flight.origin_city,
            "airline": flight.airline,
            "destination_iata": flight.destination_iata,
            "booking_url": flight.booking_url,
        }
        for flight in flights
    ]

    client = get_client()
    try:
        created = client.table("flight_links").insert(rows).execute()
    except APIError as exc:
        logger.exception("Flight link insert failed")
        if "does not exist" in str(exc) or "PGRST205" in str(exc):
            raise StorageFailed(
                "The flight_links table does not exist. Run backend/schema_flights.sql "
                "in the Supabase SQL editor."
            ) from exc
        raise StorageFailed(f"Could not save the flight links: {exc.message}") from exc

    return [FlightLinkOut(**row) for row in created.data]


def get_storefront(storefront_id: str) -> StorefrontOut:
    """Fetch a storefront with its affiliate links in a single joined query."""
    client = get_client()
    try:
        result = (
            client.table("storefronts")
            .select(
                "id, creator_id, video_url, video_title, created_at, marker_used, "
                "affiliate_links(*), flight_links(*)"
            )
            .eq("id", storefront_id)
            .limit(1)
            .execute()
        )
    except APIError as exc:
        logger.exception("Storefront fetch failed for %s", storefront_id)
        raise StorageFailed(f"Could not load the storefront: {exc.message}") from exc

    if not result.data:
        raise StorefrontNotFound("No storefront exists with that ID.")

    row = result.data[0]
    by_created = lambda link: link.get("created_at") or ""
    links = sorted(row.pop("affiliate_links", None) or [], key=by_created)
    flights = sorted(row.pop("flight_links", None) or [], key=by_created)
    return StorefrontOut(
        **row,
        affiliate_links=[AffiliateLinkOut(**link) for link in links],
        flight_links=[FlightLinkOut(**flight) for flight in flights],
    )


# --- Click tracking --------------------------------------------------------


def record_click(
    storefront_id: str,
    link_id: str,
    link_type: str,
    referrer: str | None,
    user_agent: str | None,
) -> None:
    """Insert one outbound click.

    Never raises: a failed analytics write must not surface to the visitor,
    who has already left for the booking site by the time this runs.
    """
    try:
        get_client().table("link_clicks").insert(
            {
                "storefront_id": storefront_id,
                "link_id": link_id,
                "link_type": link_type,
                "referrer": (referrer or "")[:500] or None,
                "user_agent": (user_agent or "")[:500] or None,
            }
        ).execute()
    except APIError as exc:
        if "does not exist" in str(exc) or "PGRST205" in str(exc):
            logger.error(
                "link_clicks table missing -- run backend/schema_clicks.sql. Click dropped."
            )
        else:
            logger.warning("Could not record click: %s", exc)
    except Exception:
        logger.warning("Could not record click", exc_info=True)


def get_storefront_stats(storefront_id: str) -> dict:
    """Aggregate click counts for one storefront."""
    from datetime import datetime, timedelta, timezone

    client = get_client()
    try:
        result = (
            client.table("link_clicks")
            .select("link_id, link_type, clicked_at")
            .eq("storefront_id", storefront_id)
            .execute()
        )
    except APIError as exc:
        if "does not exist" in str(exc) or "PGRST205" in str(exc):
            raise StorageFailed(
                "The link_clicks table does not exist. Run backend/schema_clicks.sql "
                "in the Supabase SQL editor."
            ) from exc
        raise StorageFailed(f"Could not load stats: {exc.message}") from exc

    rows = result.data or []
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    by_link: dict[str, int] = {}
    recent = 0
    for row in rows:
        by_link[row["link_id"]] = by_link.get(row["link_id"], 0) + 1
        stamp = row.get("clicked_at") or ""
        try:
            if datetime.fromisoformat(stamp.replace("Z", "+00:00")) >= cutoff:
                recent += 1
        except ValueError:
            pass

    return {
        "storefront_id": storefront_id,
        "total_clicks": len(rows),
        "hotel_clicks": sum(1 for r in rows if r["link_type"] == "hotel"),
        "flight_clicks": sum(1 for r in rows if r["link_type"] == "flight"),
        "clicks_last_30_days": recent,
        "by_link": by_link,
    }
