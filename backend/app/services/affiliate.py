"""Affiliate link mapping.

Hotels get a Stay22 Allez link, which sends each visitor to the specific
property on whichever of Booking.com, Expedia, Hotels.com, Agoda or Vrbo is
most likely to convert. Flights get an Aviasales pre-filled search form, with
the destination resolved to a real IATA code.

Each link carries the creator's identity -- Stay22's `campaign` for hotels,
the SubID inside Travelpayouts' `marker` for flights -- which is what the
monthly payout is split by. Both are passed in by the caller rather than read
from config, so a per-creator value cannot silently fall back to the platform's.
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

# Hotels. Travelpayouts closed its Hotellook program on October 20, 2025. Its
# links still landed on Booking.com, but the SubID was stripped on the way, so
# no booking could be traced to a creator even if one paid. "roam" lets Stay22
# pick the provider per visitor.
STAY22_ALLEZ = "https://www.stay22.com/allez/roam"

# Flights run through Aviasales, Travelpayouts' flight brand. The autocomplete
# endpoint resolves a city name to an IATA code and needs no token.
AUTOCOMPLETE_URL = "https://autocomplete.travelpayouts.com/places2"
# The pre-filled search FORM, not "/search/" -- the results page requires
# dates and errors outright without them, while the form lets the visitor pick
# their own. Params are origin-first and the adult-passenger count is
# mandatory: "?params=NYCCHC1" means New York -> Christchurch, one adult.
FLIGHT_FORM = "https://www.aviasales.com/"

_HTTP_TIMEOUT = 8


def stay22_link(hotel_name: str, location: str | None, campaign: str | None) -> str:
    """A Stay22 Allez link to one property, tagged with the creator's campaign.

    `hotelname` names the property and `address` places it; with both, Stay22
    lands on that hotel rather than a city search. A property whose location
    was never stated is placed by its own name instead.

    Stay22 asks that campaign IDs contain no commas or hyphens. SubIDs are
    letters, digits and underscores only, so they qualify as they are.
    """
    place = (location or "").strip()
    params = {"aid": config.STAY22_AID}
    if campaign:
        params["campaign"] = campaign
    params["hotelname"] = hotel_name
    params["address"] = place if place and place.casefold() != "unknown" else hotel_name
    return f"{STAY22_ALLEZ}?{urlencode(params)}"


def attach_booking_urls(hotels: list[Hotel], campaign: str | None) -> list[HotelWithLink]:
    """Append a `booking_url` to each extracted hotel.

    `campaign` is the creator's SubID. It decides whose earnings a booking
    counts toward, so it is passed in explicitly rather than defaulted.
    """
    return [
        HotelWithLink(
            hotel_name=hotel.hotel_name,
            location=hotel.location,
            booking_url=stay22_link(hotel.hotel_name, hotel.location, campaign),
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
