"""Places that are not bookable flight destinations.

A traveller books a flight to a city. "Europe", "Japan" and "the Caribbean"
produce affiliate links that go nowhere useful, so they are dropped before a
storefront is built.

The extraction prompt already forbids them; this is the backstop. Prompts are
probabilistic, and an unbookable link on a creator's page is worse than a
missing one.
"""

from __future__ import annotations

# Continents, supranational regions, and the vague phrases travel creators
# actually say. Matched case-insensitively, with a leading "the" stripped.
_REGIONS = {
    "africa", "antarctica", "asia", "europe", "north america", "south america",
    "central america", "latin america", "oceania", "australasia", "eurasia",
    "middle east", "far east", "southeast asia", "south east asia", "south asia",
    "east asia", "central asia", "western europe", "eastern europe",
    "northern europe", "southern europe", "scandinavia", "nordics", "balkans",
    "baltics", "caribbean", "west indies", "mediterranean", "pacific",
    "south pacific", "atlantic", "arctic", "sub-saharan africa", "north africa",
    "west africa", "east africa", "southern africa", "patagonia", "the alps",
    "alps", "himalayas", "andes", "sahara", "amazon", "balkan peninsula",
    "iberian peninsula", "scandinavian peninsula", "british isles",
    "the tropics", "tropics", "polynesia", "melanesia", "micronesia",
}

# Country names. A country is a valid `destination_country`, never a
# `destination_city`.
_COUNTRIES = {
    "afghanistan", "albania", "algeria", "andorra", "angola", "argentina",
    "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain",
    "bangladesh", "barbados", "belarus", "belgium", "belize", "benin", "bhutan",
    "bolivia", "bosnia", "bosnia and herzegovina", "botswana", "brazil",
    "brunei", "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon",
    "canada", "cape verde", "chad", "chile", "china", "colombia", "comoros",
    "congo", "costa rica", "croatia", "cuba", "cyprus", "czechia",
    "czech republic", "denmark", "djibouti", "dominica", "dominican republic",
    "ecuador", "egypt", "el salvador", "england", "eritrea", "estonia",
    "eswatini", "ethiopia", "fiji", "finland", "france", "gabon", "gambia",
    "georgia", "germany", "ghana", "greece", "greenland", "grenada",
    "guatemala", "guinea", "guyana", "haiti", "honduras", "hungary", "iceland",
    "india", "indonesia", "iran", "iraq", "ireland", "israel", "italy",
    "ivory coast", "jamaica", "japan", "jordan", "kazakhstan", "kenya",
    "kiribati", "kosovo", "kuwait", "kyrgyzstan", "laos", "latvia", "lebanon",
    "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg",
    "madagascar", "malawi", "malaysia", "maldives", "mali", "malta",
    "mauritania", "mauritius", "mexico", "moldova", "monaco", "mongolia",
    "montenegro", "morocco", "mozambique", "myanmar", "namibia", "nepal",
    "netherlands", "new zealand", "nicaragua", "niger", "nigeria",
    "north korea", "north macedonia", "northern ireland", "norway", "oman",
    "pakistan", "palau", "palestine", "panama", "papua new guinea", "paraguay",
    "peru", "philippines", "poland", "portugal", "qatar", "romania", "russia",
    "rwanda", "samoa", "san marino", "saudi arabia", "scotland", "senegal",
    "serbia", "seychelles", "sierra leone", "singapore", "slovakia", "slovenia",
    "solomon islands", "somalia", "south africa", "south korea", "south sudan",
    "spain", "sri lanka", "sudan", "suriname", "sweden", "switzerland", "syria",
    "taiwan", "tajikistan", "tanzania", "thailand", "togo", "tonga",
    "trinidad and tobago", "tunisia", "turkey", "turkmenistan", "tuvalu",
    "uganda", "ukraine", "united arab emirates", "united kingdom",
    "united states", "united states of america", "uruguay", "uzbekistan",
    "vanuatu", "vatican city", "venezuela", "vietnam", "wales", "yemen",
    "zambia", "zimbabwe",
    # Common spoken forms.
    "uae", "uk", "usa", "us", "america", "britain", "great britain", "holland",
    "korea", "the netherlands", "the philippines", "the gambia", "the congo",
}

# Singapore, Monaco, Vatican City and the like are both a country and the city
# you fly into, so they must survive the country filter.
_CITY_STATES = {"singapore", "monaco", "vatican city", "hong kong", "macau", "macao"}

_NOT_CITIES = (_REGIONS | _COUNTRIES) - _CITY_STATES


def normalise(place: str) -> str:
    """Lowercase, trim, and drop a leading article."""
    cleaned = (place or "").strip().casefold()
    for article in ("the ", "de ", "le "):
        if cleaned.startswith(article):
            cleaned = cleaned[len(article):]
            break
    return cleaned.strip(" .,")


def is_not_a_city(place: str) -> bool:
    """True when `place` is a country, continent or region rather than a city.

    City-states are allowed through: you really do fly to Singapore.
    """
    return normalise(place) in _NOT_CITIES
