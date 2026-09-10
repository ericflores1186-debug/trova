"""FastAPI application entrypoint.

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.errors import AppError, NoHotelsFound
from app.models.schemas import (
    ErrorResponse,
    GenerateStorefrontRequest,
    GenerateStorefrontResponse,
    StorefrontOut,
)
from app.services import affiliate, extraction, storage, transcript

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Creator Storefront API",
    description="Turns a travel video into an affiliate hotel storefront.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """Map domain errors onto status codes in one place."""
    if exc.status_code >= 500:
        logger.error("%s: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "extraction_model": config.EXTRACTION_MODEL}


@app.post(
    "/api/generate-storefront",
    response_model=GenerateStorefrontResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def generate_storefront(payload: GenerateStorefrontRequest) -> GenerateStorefrontResponse:
    """Transcript -> AI extraction -> affiliate links -> Supabase."""
    video_id = transcript.parse_video_id(payload.video_url)
    logger.info("Generating storefront for video %s", video_id)

    video_title = transcript.fetch_video_title(video_id)
    text = transcript.fetch_transcript(video_id)

    found = extraction.extract_travel(text)
    # Flights carry the storefront when a video never names where they stayed,
    # so only a video with neither is a dead end.
    if not found.hotels and not found.flights:
        raise NoHotelsFound(
            "No hotels or destinations were mentioned in this video. "
            "Try a travel vlog that names where they stayed or where they went."
        )

    linked_hotels = affiliate.attach_booking_urls(found.hotels)
    linked_flights = affiliate.attach_flight_urls(found.flights)

    creator_id = storage.upsert_creator(payload.creator_name, payload.youtube_handle)
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    storefront_id = storage.create_storefront(
        creator_id=creator_id,
        video_url=video_url,
        video_title=video_title,
    )
    links = storage.create_affiliate_links(storefront_id, linked_hotels)
    flights = storage.create_flight_links(storefront_id, linked_flights)

    logger.info(
        "Storefront %s created with %d hotel(s) and %d flight(s)",
        storefront_id,
        len(links),
        len(flights),
    )

    return GenerateStorefrontResponse(
        storefront_id=storefront_id,
        video_title=video_title,
        hotels_found=len(links),
        flights_found=len(flights),
        storefront=StorefrontOut(
            id=storefront_id,
            creator_id=creator_id,
            video_url=video_url,
            video_title=video_title,
            affiliate_links=links,
            flight_links=flights,
        ),
    )


@app.get(
    "/api/storefronts/{storefront_id}",
    response_model=StorefrontOut,
    responses={404: {"model": ErrorResponse}},
)
async def read_storefront(storefront_id: str) -> StorefrontOut:
    """Public read for the storefront page."""
    return storage.get_storefront(storefront_id)
