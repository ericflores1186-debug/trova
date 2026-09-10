"""Request / response models for the public API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Extraction ------------------------------------------------------------


class Hotel(BaseModel):
    """One lodging mentioned in a video.

    Doubles as the JSON schema handed to Claude for structured extraction, so
    keep the field names identical to the `affiliate_links` columns.
    """

    hotel_name: str = Field(description="The name of the hotel, resort, or lodging as spoken in the video.")
    location: str = Field(description="City, region and/or country of the property. 'Unknown' if never stated.")


class Flight(BaseModel):
    """One journey mentioned in a video.

    A video almost always involves getting somewhere, even when the creator
    never names where they slept -- so flights give a storefront something to
    sell when no lodging is mentioned.
    """

    destination_city: str = Field(description="The city or airport the creator travelled TO.")
    destination_country: Optional[str] = Field(
        default=None, description="Country of the destination, if the transcript supports it."
    )
    origin_city: Optional[str] = Field(
        default=None, description="Where they departed from, only if explicitly stated."
    )
    airline: Optional[str] = Field(
        default=None, description="Airline name, only if explicitly stated."
    )


class TravelExtraction(BaseModel):
    """Everything bookable that the extraction model found in one transcript.

    A JSON Schema root must be an object, so both arrays nest one level.
    """

    hotels: list[Hotel] = Field(
        default_factory=list, description="Every named lodging mentioned. Empty if none."
    )
    flights: list[Flight] = Field(
        default_factory=list, description="Every destination flown or travelled to. Empty if none."
    )


# Kept as an alias so older imports do not break.
HotelList = TravelExtraction


class HotelWithLink(Hotel):
    booking_url: str


class FlightWithLink(Flight):
    booking_url: str
    destination_iata: Optional[str] = None


# --- Requests --------------------------------------------------------------


class GenerateStorefrontRequest(BaseModel):
    video_url: str = Field(
        description="Full YouTube URL or bare 11-character video ID.",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )
    creator_name: Optional[str] = Field(default=None, max_length=200)
    youtube_handle: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Stable identifier for the creator, e.g. '@wanderlust'. Used to de-duplicate creators.",
    )
    travelpayouts_marker: Optional[str] = Field(
        default=None,
        max_length=32,
        pattern=r"^\d*$",
        description=(
            "The creator's own Travelpayouts marker, so commission on this "
            "storefront pays them. Digits only. Omit to keep whatever marker "
            "the creator already has, or the platform default if they have none."
        ),
    )


# --- Responses -------------------------------------------------------------


class AffiliateLinkOut(BaseModel):
    id: str
    hotel_name: str
    location: str
    booking_url: str
    created_at: Optional[datetime] = None


class FlightLinkOut(BaseModel):
    id: str
    destination_city: str
    destination_iata: Optional[str] = None
    destination_country: Optional[str] = None
    origin_city: Optional[str] = None
    airline: Optional[str] = None
    booking_url: str
    created_at: Optional[datetime] = None


class StorefrontOut(BaseModel):
    id: str
    creator_id: str
    video_url: str
    video_title: str
    created_at: Optional[datetime] = None
    # Which Travelpayouts marker this storefront's links pay. Needed by the
    # page to assemble flight deeplinks in the browser.
    marker_used: Optional[str] = None
    affiliate_links: list[AffiliateLinkOut] = Field(default_factory=list)
    flight_links: list[FlightLinkOut] = Field(default_factory=list)


class GenerateStorefrontResponse(BaseModel):
    storefront_id: str
    # Which marker these links will actually pay. Surfaced so the UI can warn
    # a creator that they are not the one earning.
    marker_used: str
    marker_is_creators: bool
    video_title: str
    hotels_found: int
    flights_found: int
    storefront: StorefrontOut


class ClickIn(BaseModel):
    """One outbound click, reported by the storefront page."""

    storefront_id: str
    link_id: str
    link_type: Literal["hotel", "flight"]


class StorefrontStats(BaseModel):
    storefront_id: str
    total_clicks: int
    hotel_clicks: int
    flight_clicks: int
    clicks_last_30_days: int
    by_link: dict[str, int] = Field(
        default_factory=dict, description="Click count keyed by affiliate/flight link id."
    )


class ErrorResponse(BaseModel):
    code: str
    message: str
