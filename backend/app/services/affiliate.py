"""Travelpayouts affiliate link mapping.

Hotels get a marker-tagged Hotellook search deeplink, which hands off to
Booking.com carrying the affiliate label. Flights get an Aviasales pre-filled
search form, with the destination resolved to a real IATA code.

Both carry `marker`, which is what decides who is paid. It is always passed in
by the caller rather than read from config, so a per-creator value cannot
silently fall back to the platform's.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from urllib.parse import urlencode

import requests

from app import config
from app.models.schemas import Flight, FlightWithLink, Hotel, HotelWithLink

logger = logging.getLogger(__name__)


class LookupUnavailable(Exception):
    """The autocomplete endpoint could not be reached.

    Distinct from "no match": a network failure must not silently delete a
    creator's destinations, whereas a genuine no-match means the place has no
    airport and is not a flight destination at all.
    """

# Real Travelpayouts endpoints.
SEARCH_DEEPLINK = "https://search.hotellook.com/hotels"

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


def attach_booking_urls(hotels: list[Hotel], marker: str) -> list[HotelWithLink]:
    """Append a `booking_url` to each extracted hotel.

    `marker` decides who gets paid, so it is always passed in explicitly
    rather than read from config -- a per-creator value must never silently
    fall back to the platform's.

    There used to be a lookup here that resolved each property to a specific
    Hotellook page via `engine.hotellook.com/api/v2/lookup.json`. That endpoint
    now returns 404 for everyone, token or not, so the call only ever cost a
    round trip per hotel and returned nothing.

    The search deeplink is what ships instead. It is not a downgrade in
    practice: it hands off to Booking.com carrying the affiliate label, so the
    link works and the marker is tracked. Resolving a specific hotel page today
    would mean the signed, two-step Hotel Search API -- worth doing only if the
    extra click measurably costs conversions.
    """
    return [
        HotelWithLink(
            hotel_name=hotel.hotel_name,
            location=hotel.location,
            booking_url=_search_deeplink(hotel, marker),
        )
        for hotel in hotels
    ]


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


def _normalise_place(value: str) -> str:
    """Casefold and strip punctuation/accents so names compare sensibly."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", stripped.casefold())


def _lookup_iata(city: str, country: str | None = None) -> str | None:
    """Resolve a city to its IATA code, or None if there is no real match.

    The autocomplete endpoint is fuzzy and always answers: "Kyoto" comes back
    as Nice, France, and "Nara" as Narathiwat, Thailand -- because neither
    Japanese city has an airport. Taking the first result blindly sent
    travellers to the wrong continent, so the name (and country, when known)
    must actually match what was asked for.

    Returns None both when nothing matches and when the lookup fails; the
    caller distinguishes the two.
    """
    try:
        response = requests.get(
            AUTOCOMPLETE_URL,
            params={"term": city, "locale": "en", "types[]": "city"},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json() or []
    except Exception as exc:
        logger.warning("IATA lookup failed for %r: %s", city, exc)
        raise LookupUnavailable(str(exc)) from exc

    wanted = _normalise_place(city)
    wanted_country = _normalise_place(country) if country else None

    # An exact name match is the signal that matters. Country only breaks ties
    # between same-named cities -- it cannot veto, because the two sources name
    # countries differently: a transcript says "Hong Kong, China" while the
    # endpoint says "Hong Kong, Hong Kong", and USA/United States and
    # UK/United Kingdom disagree the same way.
    name_matches = [
        result
        for result in results
        if _normalise_place(result.get("name", "")) == wanted
    ]

    if name_matches:
        if wanted_country:
            for result in name_matches:
                if _normalise_place(result.get("country_name", "")) == wanted_country:
                    return result.get("code")
        return name_matches[0].get("code")

    logger.info(
        "No airport matches %r (best guess was %r) -- not a flyable destination",
        city,
        (results[0].get("name") if results else None),
    )
    return None


def attach_flight_urls(flights: list[Flight], marker: str) -> list[FlightWithLink]:
    """Append a `booking_url` to each extracted destination."""
    linked: list[FlightWithLink] = []

    for flight in flights:
        # Resolve the destination IATA even in mock mode: the storefront page
        # needs it to assemble a deeplink once it knows the visitor's own
        # airport. The autocomplete endpoint requires no token.
        try:
            destination_iata = _lookup_iata(
                flight.destination_city, flight.destination_country
            )
        except LookupUnavailable:
            # Endpoint down. Keep the destination with a generic link rather
            # than deleting it -- a temporary outage must not silently shrink
            # a storefront.
            linked.append(
                FlightWithLink(
                    destination_city=flight.destination_city,
                    destination_country=flight.destination_country,
                    origin_city=flight.origin_city,
                    airline=flight.airline,
                    destination_iata=None,
                    booking_url=_flight_fallback_url(marker),
                )
            )
            continue

        if not destination_iata:
            # No airport answers to this name, so it is a place you reach by
            # train or car once you are already there -- Kyoto, Nara, a
            # national park. Not a flight, and a link to a fuzzy-matched
            # airport on another continent is worse than no link at all.
            logger.info("Dropping %r: no airport, not a flight destination", flight.destination_city)
            continue

        try:
            origin_iata = (
                _lookup_iata(flight.origin_city) if flight.origin_city else None
            )
        except LookupUnavailable:
            origin_iata = None

        linked.append(
            FlightWithLink(
                destination_city=flight.destination_city,
                destination_country=flight.destination_country,
                origin_city=flight.origin_city,
                airline=flight.airline,
                destination_iata=destination_iata,
                booking_url=_flight_iata_deeplink(origin_iata, destination_iata, marker),
            )
        )

    return linked
