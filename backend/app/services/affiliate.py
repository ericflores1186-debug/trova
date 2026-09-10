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
FLIGHT_DEEPLINK = "https://www.aviasales.com/search"

_HTTP_TIMEOUT = 8


def _search_deeplink(hotel: Hotel) -> str:
    """Marker-tagged search deeplink. Always resolvable, never a dead link."""
    query = f"{hotel.hotel_name} {hotel.location}".strip() if hotel.location != "Unknown" else hotel.hotel_name
    params = {
        "destination": query,
        "marker": config.TRAVELPAYOUTS_MARKER,
    }
    return f"{SEARCH_DEEPLINK}?{urlencode(params)}"


def _hotel_deeplink(hotel_id: int | str) -> str:
    params = {"hotelId": str(hotel_id), "marker": config.TRAVELPAYOUTS_MARKER}
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


def attach_booking_urls(hotels: list[Hotel]) -> list[HotelWithLink]:
    """Append a `booking_url` to each extracted hotel."""
    linked: list[HotelWithLink] = []

    for hotel in hotels:
        booking_url = None

        if not config.TRAVELPAYOUTS_MOCK:
            hotel_id = _lookup_hotel_id(hotel)
            if hotel_id:
                booking_url = _hotel_deeplink(hotel_id)

        linked.append(
            HotelWithLink(
                hotel_name=hotel.hotel_name,
                location=hotel.location,
                booking_url=booking_url or _search_deeplink(hotel),
            )
        )

    return linked


# --- Flights ---------------------------------------------------------------


def _flight_search_deeplink(flight: Flight) -> str:
    """Marker-tagged Aviasales search. Always resolvable, never a dead link."""
    destination = flight.destination_city
    if flight.destination_country:
        destination = f"{destination}, {flight.destination_country}"

    params = {"destination": destination, "marker": config.TRAVELPAYOUTS_MARKER}
    if flight.origin_city:
        params["origin"] = flight.origin_city
    return f"{FLIGHT_DEEPLINK}?{urlencode(params)}"


def _flight_iata_deeplink(origin_iata: str | None, destination_iata: str) -> str:
    params = {"destination_iata": destination_iata, "marker": config.TRAVELPAYOUTS_MARKER}
    if origin_iata:
        params["origin_iata"] = origin_iata
    return f"{FLIGHT_DEEPLINK}?{urlencode(params)}"


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


def attach_flight_urls(flights: list[Flight]) -> list[FlightWithLink]:
    """Append a `booking_url` to each extracted destination."""
    linked: list[FlightWithLink] = []

    for flight in flights:
        booking_url = None

        if not config.TRAVELPAYOUTS_MOCK:
            destination_iata = _lookup_iata(flight.destination_city)
            if destination_iata:
                origin_iata = _lookup_iata(flight.origin_city) if flight.origin_city else None
                booking_url = _flight_iata_deeplink(origin_iata, destination_iata)

        linked.append(
            FlightWithLink(
                destination_city=flight.destination_city,
                destination_country=flight.destination_country,
                origin_city=flight.origin_city,
                airline=flight.airline,
                booking_url=booking_url or _flight_search_deeplink(flight),
            )
        )

    return linked
