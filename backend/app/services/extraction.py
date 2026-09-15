"""Hotel / lodging extraction from a transcript, using Claude.

Uses structured outputs (`messages.parse` with a Pydantic model) rather than
asking for JSON in prose and parsing it back. The API constrains generation to
the schema, so `parsed_output` is always a valid `HotelList` -- no regex
scraping of code fences, no `json.loads` failures on a chatty preamble.
"""

from __future__ import annotations

import base64
import logging

import anthropic

from app import config
from app.errors import ExtractionFailed
from app.models.schemas import Flight, Hotel, TravelExtraction
from app.services import geo

logger = logging.getLogger(__name__)

# Built on first use so the service still starts in MOCK_EXTRACTION mode with
# no Anthropic credentials present at all.
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Resolves ANTHROPIC_API_KEY (or an `ant auth login` profile) from the
    environment. Never hardcode a key here."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


# Canned result for MOCK_EXTRACTION. Deliberately labelled so nobody mistakes a
# mocked storefront for a real one.
_MOCK_HOTELS = [
    Hotel(hotel_name="[MOCK] Hoshinoya Kyoto", location="Arashiyama, Kyoto, Japan"),
    Hotel(hotel_name="[MOCK] The Ritz-Carlton Kyoto", location="Nakagyo Ward, Kyoto, Japan"),
    Hotel(hotel_name="[MOCK] Nazuna Kyoto Gosho", location="Kyoto, Japan"),
    Hotel(hotel_name="[MOCK] Ryokan Yoshida-sanso", location="Unknown"),
]

_MOCK_FLIGHTS = [
    Flight(destination_city="[MOCK] Kyoto", destination_country="Japan", origin_city="London"),
    Flight(destination_city="[MOCK] Osaka", destination_country="Japan"),
]

# Output is a short JSON array; this ceiling exists only to keep a pathological
# response from being truncated mid-object.
_MAX_TOKENS = 16000

SYSTEM_PROMPT = """\
You extract lodging mentions from travel video transcripts.

Return every hotel, resort, villa, hostel, guesthouse, lodge, riad, ryokan, \
boutique inn, or other named place to stay that the speaker mentions.

Rules:
1. Extract ONLY named lodging. A property must have a proper name to qualify.
2. Do NOT extract restaurants, cafes, bars, clubs, spas, tour operators, \
airlines, airports, car rentals, museums, beaches, national parks, or any \
other attraction -- even when the speaker praises them at length.
3. Do NOT extract a city, region, or country on its own. Those are locations, \
not lodging.
4. Do NOT invent, infer, or complete names. If the transcript says "this \
little place by the beach" with no name, skip it.
5. Fix obvious transcription artefacts in a name (casing, split words) but \
never change which property is being named.
6. Set `location` to the most specific place the transcript actually supports \
-- "Kyoto, Japan", "Tulum, Mexico", "Amalfi Coast, Italy". If the transcript \
never says where the property is, set it to exactly "Unknown". Do not guess \
from the property's name.
7. List each property once, even if it is mentioned many times. A named room, \
suite or villa inside a hotel -- "the Hardwood Suite", "a Presidential Suite" \
-- is part of that hotel, not a property of its own: list the hotel once, and \
never the room. A hotel whose own name contains "Suites" (Embassy Suites) is \
still a hotel.
8. If the transcript mentions no named lodging at all, return an empty array. \
An empty array is a correct and expected answer -- never pad it.

FLIGHTS -- fill in `flights` as well.

Return each distinct place the speaker travelled TO on this trip. A travel \
video almost always involves going somewhere, even when no hotel is named.

These become flight-search links, so return only places a traveller would \
realistically FLY to -- a city with an airport, or the nearest major city a \
visitor would book into.

Rules:
9.  A destination qualifies when the speaker actually went there on this trip \
AND it is somewhere you could book a flight to. "We landed in Queenstown", \
"we spent three days in Lisbon", "first stop was Tokyo".
10. Do NOT include stops reached only by car, train, or boat once the traveller \
was already in the region -- villages, beaches, national parks, day trips, \
road-trip waypoints. Those belong to a destination already in the list, not to \
a flight of their own.
11. DO include a long layover city if the speaker left the airport, and each \
separate leg of a multi-country trip.
12. Do NOT include places they only talk about, recommend for next time, \
compare against, or say they skipped.
13. `destination_city` must be a CITY, never a country, region, island, or \
continent. "New Zealand", "Japan", "the Alps", "Southeast Asia" are all \
invalid values -- a traveller books a flight to a city, not to a country.
    - Name the specific city the speaker actually went to.
    - If the speaker names a region but not a city, use the main airport city \
      a visitor would book into for that region, and only when it is obvious.
    - If you cannot identify any city with confidence, omit the entry \
      entirely. A missing destination is better than an unbookable one.
    - Never emit both a country and a city from that same country. If you \
      have "Christchurch", do not also emit "New Zealand".
    Set `destination_country` to that city's country when you know it.
14. Set `origin_city` ONLY if the speaker says where they departed from. \
Never assume a home city.
15. Set `airline` ONLY if an airline is named out loud.
16. One entry per destination, even across multiple visits. For a multi-stop \
trip, list each stop.
17. If the speaker never goes anywhere -- a studio piece, a review filmed at \
home, a list video -- return an empty array.

Transcripts are auto-generated, so expect missing punctuation and misheard \
words. Judge from context.\
"""

_USER_TEMPLATE = (
    "Extract every named lodging and every destination travelled to in this "
    "travel video transcript.\n\n"
    "<transcript>\n{text}\n</transcript>"
)

# A TikTok or Instagram post is not one transcript. Each part is labelled so
# the model can weigh them: a tagged hotel is a deliberate statement, a
# misheard name in the auto-captions is not.
_SHORT_VIDEO_TEMPLATE = (
    "Extract every named lodging and every destination travelled to in this "
    "{platform} travel post.\n\n"
    "The post arrives in labelled parts instead of one transcript: the "
    "creator's written <caption>, the <on_screen_text> shown over the video, "
    "the <tagged_location> they attached, and the <spoken_words>. Any part can "
    "be missing. All of them describe the same video, so a property named in "
    "any one part counts as mentioned.\n"
    "- A tagged location whose type is a hotel, resort or other lodging names "
    "the property the post is about. Include it, and take `location` from its "
    "address.\n"
    "- An @mention or hashtag can name a property, as in #fairmontorchidhawaii. "
    "Count one only when it names a specific property -- never a hotel brand "
    "or loyalty programme on its own, such as @Marriott Bonvoy.\n"
    "- Spoken words are auto-transcribed and mishear names. When the caption or "
    "on-screen text names the same place, use that spelling.\n\n"
    "{images_note}"
    "{text}"
)

# Images invite identifying a hotel by how it looks. A storefront link to a
# guessed property is worse than no link, so only written text counts. And
# unusual names get "corrected" into familiar words -- "Casa Lawa" on a slide
# came back as "Casa Lava" -- so names are copied exactly as written.
_SLIDES_NOTE = (
    "This is a photo post, and its slides are attached above as images, in "
    "order. Read the text written on each slide: slideshow creators often name "
    "each property only there, with its location beneath it. Only written text "
    "counts -- never identify a property from how it looks. Copy each name "
    "exactly as written, letter for letter, even when it resembles a more "
    "familiar word.\n\n"
)

_COVER_NOTE = (
    "The post's cover image is attached above. Read any text written on it: "
    "creators often put the property's name or city there. Only written text "
    "counts -- never identify a property from how it looks. Copy each name "
    "exactly as written, letter for letter, even when it resembles a more "
    "familiar word.\n\n"
)


def _chunk(transcript: str, size: int) -> list[str]:
    """Split an over-long transcript on whitespace boundaries.

    Long transcripts are split and extracted per chunk, then merged -- never
    truncated, which would silently drop hotels from the back half of a video.
    """
    if len(transcript) <= size:
        return [transcript]

    chunks: list[str] = []
    start = 0
    while start < len(transcript):
        end = min(start + size, len(transcript))
        if end < len(transcript):
            boundary = transcript.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(transcript[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


def _extract_chunk(
    transcript: str,
    template: str = _USER_TEMPLATE,
    images: list[tuple[bytes, str]] | None = None,
) -> TravelExtraction:
    prompt = template.format(text=transcript)
    content: str | list[dict] = prompt
    if images:
        # Images before the text that refers to them.
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(data).decode("ascii"),
                },
            }
            for data, media_type in images
        ] + [{"type": "text", "text": prompt}]

    try:
        response = _get_client().messages.parse(
            model=config.EXTRACTION_MODEL,
            max_tokens=_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
            output_format=TravelExtraction,
        )
    except anthropic.NotFoundError as exc:
        raise ExtractionFailed(
            f"Model '{config.EXTRACTION_MODEL}' is not available to this API key. "
            "Check EXTRACTION_MODEL in your .env."
        ) from exc
    except anthropic.AuthenticationError as exc:
        raise ExtractionFailed("Anthropic rejected the API key.") from exc
    except anthropic.RateLimitError as exc:
        raise ExtractionFailed("Anthropic rate limit reached. Please retry in a moment.") from exc
    except anthropic.APIStatusError as exc:
        if exc.status_code >= 500:
            raise ExtractionFailed("Anthropic is temporarily unavailable. Please retry.") from exc
        raise ExtractionFailed(f"Extraction request rejected: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ExtractionFailed("Could not reach the Anthropic API.") from exc

    if response.stop_reason == "max_tokens":
        raise ExtractionFailed("Extraction response was truncated. Try a shorter video.")

    parsed = response.parsed_output
    if parsed is None:
        raise ExtractionFailed("The model returned no structured output.")

    logger.info(
        "Extracted %d lodging(s) and %d destination(s) from %d chars "
        "(in=%d out=%d tokens)",
        len(parsed.hotels),
        len(parsed.flights),
        len(transcript),
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return parsed


def _dedupe_hotels(hotels: list[Hotel]) -> list[Hotel]:
    seen: dict[tuple[str, str], Hotel] = {}
    for hotel in hotels:
        name = hotel.hotel_name.strip()
        location = (hotel.location or "").strip() or "Unknown"
        if not name:
            continue
        seen.setdefault(
            (name.casefold(), location.casefold()),
            Hotel(hotel_name=name, location=location),
        )
    return list(seen.values())


def _dedupe_flights(flights: list[Flight]) -> list[Flight]:
    """De-duplicate on destination alone.

    A multi-chunk transcript often yields the same city twice, once with a
    country and once without; keeping the richer of the two beats keeping both.
    """
    # A country is not a bookable destination. The prompt forbids emitting one,
    # but prompts are probabilistic -- drop any entry whose "city" is really a
    # country named by another entry, or by itself.
    countries = {
        (f.destination_country or "").strip().casefold()
        for f in flights
        if (f.destination_country or "").strip()
    }

    seen: dict[str, Flight] = {}
    for flight in flights:
        city = (flight.destination_city or "").strip()
        if not city:
            continue
        key = city.casefold()
        if key in countries or geo.is_not_a_city(city):
            logger.info(
                "Dropping %r as a destination: not a bookable city", city
            )
            continue
        candidate = Flight(
            destination_city=city,
            destination_country=(flight.destination_country or "").strip() or None,
            origin_city=(flight.origin_city or "").strip() or None,
            airline=(flight.airline or "").strip() or None,
        )
        existing = seen.get(key)
        if existing is None:
            seen[key] = candidate
            continue
        # Merge: prefer whichever entry actually has each field filled in.
        seen[key] = Flight(
            destination_city=existing.destination_city,
            destination_country=existing.destination_country or candidate.destination_country,
            origin_city=existing.origin_city or candidate.origin_city,
            airline=existing.airline or candidate.airline,
        )
    return list(seen.values())


def extract_travel(transcript: str) -> TravelExtraction:
    """Return the de-duplicated lodgings and destinations found in `transcript`."""
    if config.MOCK_EXTRACTION:
        logger.warning(
            "MOCK_EXTRACTION is on -- returning canned data, ignoring the "
            "%d-char transcript. Unset it in .env for real results.",
            len(transcript),
        )
        return TravelExtraction(hotels=list(_MOCK_HOTELS), flights=list(_MOCK_FLIGHTS))

    hotels: list[Hotel] = []
    flights: list[Flight] = []
    for chunk in _chunk(transcript, config.TRANSCRIPT_CHUNK_CHARS):
        result = _extract_chunk(chunk)
        hotels.extend(result.hotels)
        flights.extend(result.flights)

    return TravelExtraction(
        hotels=_dedupe_hotels(hotels),
        flights=_dedupe_flights(flights),
    )


def extract_short_video(
    document: str,
    images: list[tuple[bytes, str]] | None = None,
    *,
    platform: str = "TikTok",
    images_kind: str = "slides",
) -> TravelExtraction:
    """Lodgings and destinations from a TikTok or Instagram post.

    `images` are the post's slides or its cover, as `images_kind` says.

    Not chunked: a post's caption, on-screen text and captions together run to
    a few thousand characters, far inside one request.

    Deliberately extracts nothing else. Asking for a page title in the same
    structured response made the model run away inside the title string --
    pages of repeated text -- and return no hotels at all.
    """
    if not document.strip() and not images:
        return TravelExtraction()

    if config.MOCK_EXTRACTION:
        logger.warning(
            "MOCK_EXTRACTION is on -- returning canned data, ignoring the "
            "%d-char %s post. Unset it in .env for real results.",
            len(document),
            platform,
        )
        return TravelExtraction(hotels=list(_MOCK_HOTELS), flights=list(_MOCK_FLIGHTS))

    # str.replace, not format(): {text} must survive to be filled in by
    # _extract_chunk.
    note = {"slides": _SLIDES_NOTE, "cover": _COVER_NOTE}.get(images_kind, "") if images else ""
    template = _SHORT_VIDEO_TEMPLATE.replace("{platform}", platform).replace("{images_note}", note)
    result = _extract_chunk(document, template=template, images=images)
    return TravelExtraction(
        hotels=_dedupe_hotels(result.hotels),
        flights=_dedupe_flights(result.flights),
    )


def extract_hotels(transcript: str) -> list[Hotel]:
    """Backwards-compatible wrapper returning lodgings only."""
    return extract_travel(transcript).hotels
