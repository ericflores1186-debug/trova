"""Derive flight destinations from the hotels on a storefront.

A hotel review never narrates travelling anywhere -- the creator is already
standing in the lobby -- so extraction correctly finds no flights. But a viewer
who wants that hotel still has to get there, and a storefront with a Hong Kong
hotel and no way to fly to Hong Kong is leaving money on the page.

Every hotel implies a destination. This turns hotel locations into flight
entries, without duplicating anything extraction already found.
"""

from __future__ import annotations

import logging

from app.models.schemas import Flight, Hotel
from app.services import geo

logger = logging.getLogger(__name__)

# "Arashiyama, Kyoto, Japan" -> city "Arashiyama", country "Japan". Locations
# come from the transcript, so they are free text rather than structured.
_UNKNOWN = {"", "unknown"}


def _split_location(location: str) -> tuple[str, str | None]:
    """Best-effort city and country from a comma-separated location string."""
    parts = [part.strip() for part in (location or "").split(",") if part.strip()]
    if not parts:
        return "", None
    if len(parts) == 1:
        return parts[0], None

    country = parts[-1]
    # The city is the part immediately before the country. For a three-part
    # location like "Arashiyama, Kyoto, Japan" that is "Kyoto" -- the airport
    # city rather than the neighbourhood.
    city = parts[-2]
    return city, country


def candidates_from_hotels(hotels: list[Hotel]) -> list[Flight]:
    """Flight destinations implied by where the hotels are.

    Returns candidates only. The caller resolves each to an airport, which is
    what decides whether it is somewhere you can actually fly to -- a hotel in
    Kyoto adds nothing, because Kyoto has no airport.
    """
    seen: dict[str, Flight] = {}

    for hotel in hotels:
        location = (hotel.location or "").strip()
        if location.casefold() in _UNKNOWN:
            continue

        city, country = _split_location(location)
        if not city or geo.is_not_a_city(city):
            # A location of just "Japan" names no city to fly to.
            continue

        key = city.casefold()
        if key not in seen:
            seen[key] = Flight(
                destination_city=city,
                destination_country=country if country and not geo.is_not_a_city(city) else country,
            )

    if seen:
        logger.info(
            "Hotels imply %d destination(s): %s",
            len(seen),
            ", ".join(f.destination_city for f in seen.values()),
        )
    return list(seen.values())


def merge(extracted: list[Flight], derived: list[Flight]) -> list[Flight]:
    """Append derived destinations that extraction did not already find.

    Extraction wins on conflicts: it saw the transcript and may know the origin
    or the airline, which a hotel address cannot tell us.
    """
    known = {(f.destination_city or "").casefold() for f in extracted}
    additions = [f for f in derived if (f.destination_city or "").casefold() not in known]
    return [*extracted, *additions]
