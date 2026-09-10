"""Travelpayouts / Hotellook affiliate link mapping.

Mocked by default (`TRAVELPAYOUTS_MOCK=true`): the request shape below is the
real Hotellook lookup endpoint, but with a placeholder token it will not
return usable IDs, so every hotel falls back to a marker-tagged search
deeplink. Those deeplinks are valid affiliate URLs -- they land the visitor on
a Hotellook search for the property, with your marker attached.

Set TRAVELPAYOUTS_MOCK=false once you have real credentials to resolve each
property to its specific hotel page.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import requests

from app import config
from app.models.schemas import Flight, FlightWithLink, Hotel, HotelWithLink

logger = logging.getLogger(__name__)

# Real Travelpayouts endpoints.
LOOKUP_URL = "https://engine.hotellook.com/api/v2/lookup.json"
SEARCH_DEEPLINK = "https://search.hotellook.com/hotels"
HOTEL_DEEPLINK = "https://search.hotellook.com/hotels"

# Flights run through Aviasales, Travelpayouts' flight brand -- same marker as
# hotels, no second account needed. The autocomplete endpoint resolves a city
# name to an IATA code and needs no token.
AUTOCOMPLETE_URL = "https://autocomplete.travelpayouts.com/places2"
# The pre-filled search FORM, not "/search/" -- the results page requires
# dates and errors outright without them, while the form lets the visitor pick
# their own. Params are origin-first and the adult-passenger count is
# mandatory: "?params=NYCCHC1" means New York -> Christchurch, one adult.
FLIGHT_FORM = "https://www.aviasales.com/"

_HTTP_TIMEOUT = 8


def _search_deeplink(hotel: Hotel, marker: str) -> str:
    """Marker-tagged search deeplink. Always resolvable, never a dead link."""
    query = f"{hotel.hotel_name} {hotel.location}".strip() if hotel.location != "Unknown" else hotel.hotel_name
    params = {
        "destination": query,
        "marker": marker,
    }
    return f"{SEARCH_DEEPLINK}?{urlencode(params)}"


def _hotel_deeplink(hotel_id: int | str, marker: str) -> str:
    params = {"hotelId": str(hotel_id), "marker": marker}
    return f"{HOTEL_DEEPLINK}?{urlencode(params)}"


def _lookup_hotel_id(hotel: Hotel) -> str | None:
    """GET the Travelpayouts lookup endpoint for this property's hotel ID.

    Returns None on any failure -- a missing ID is not worth failing the whole
    storefront over, the caller just uses the search deeplink instead.
    """
    query = hotel.hotel_name
    if hotel.location and hotel.location != "Unknown":
        query = f"{hotel.hotel_name}, {hotel.location}"

    try:
        response = requests.get(
            LOOKUP_URL,
            params={
                "query": query,
                "lang": "en",
                "lookFor": "hotel",
                "limit": 1,
                "token": config.TRAVELPAYOUTS_API_TOKEN,
            },
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        hotels = (response.json().get("results") or {}).get("hotels") or []
        if hotels:
            return hotels[0].get("id")
        logger.info("No Hotellook match for %r", query)
    except Exception:
        logger.warning("Travelpayouts lookup failed for %r", query, exc_info=True)

    return None


def attach_booking_urls(hotels: list[Hotel], marker: str) -> list[HotelWithLink]:
    """Append a `booking_url` to each extracted hotel.

    `marker` decides who gets paid, so it is always passed in explicitly
    rather than read from config -- a per-creator value must never silently
    fall back to the platform's.
    """
    linked: list[HotelWithLink] = []

    for hotel in hotels:
        booking_url = None

        if not config.TRAVELPAYOUTS_MOCK:
            hotel_id = _lookup_hotel_id(hotel)
            if hotel_id:
                booking_url = _hotel_deeplink(hotel_id, marker)

        linked.append(
            HotelWithLink(
                hotel_name=hotel.hotel_name,
                location=hotel.location,
                booking_url=booking_url or _search_deeplink(hotel, marker),
            )
        )

    return linked


# --- Flights ---------------------------------------------------------------


def _flight_fallback_url(marker: str) -> str:
    """A working, marker-tagged Aviasales form with nothing pre-filled.

    Used when no IATA code could be resolved. The visitor fills it in
    themselves -- weaker than a deeplink, but it loads and it still earns.
    """
    return f"{FLIGHT_FORM}?{urlencode({'marker': marker})}"


def build_flight_params(origin_iata: str | None, destination_iata: str) -> str:
    """Build the Aviasales `params` value: route, then adult count.

    Origin comes first. Without one the destination is read as the departure
    point and the form fills backwards, so callers that can know the visitor's
    airport should always pass it.
    """
    route = f"{origin_iata or ''}{destination_iata}".upper()
    return f"{route}1"  # trailing 1 = one adult; the link does not work without it


def _flight_iata_deeplink(origin_iata: str | None, destination_iata: str, marker: str) -> str:
    params = build_flight_params(origin_iata, destination_iata)
    return f"{FLIGHT_FORM}?{urlencode({'params': params, 'marker': marker})}"


def _lookup_iata(city: str) -> str | None:
    """Resolve a city name to its IATA code via Travelpayouts autocomplete.

    Returns None on any failure -- the caller falls back to a name-based
    search link rather than failing the storefront.
    """
    try:
        response = requests.get(
            AUTOCOMPLETE_URL,
            params={"term": city, "locale": "en", "types[]": "city"},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json() or []
        if results:
            return results[0].get("code")
        logger.info("No IATA match for %r", city)
    except Exception as exc:
        logger.warning("IATA lookup failed for %r: %s", city, exc)

    return None


def attach_flight_urls(flights: list[Flight], marker: str) -> list[FlightWithLink]:
    """Append a `booking_url` to each extracted destination."""
    linked: list[FlightWithLink] = []

    for flight in flights:
        # Resolve the destination IATA even in mock mode: the storefront page
        # needs it to assemble a deeplink once it knows the visitor's own
        # airport. The autocomplete endpoint requires no token.
        destination_iata = _lookup_iata(flight.destination_city)
        origin_iata = (
            _lookup_iata(flight.origin_city)
            if flight.origin_city and destination_iata
            else None
        )

        booking_url = (
            _flight_iata_deeplink(origin_iata, destination_iata, marker)
            if destination_iata
            else _flight_fallback_url(marker)
        )

        linked.append(
            FlightWithLink(
                destination_city=flight.destination_city,
                destination_country=flight.destination_country,
                origin_city=flight.origin_city,
                airline=flight.airline,
                destination_iata=destination_iata,
                booking_url=booking_url,
            )
        )

    return linked
