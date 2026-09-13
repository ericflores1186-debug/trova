"""FastAPI application entrypoint.

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.errors import AppError, NoHotelsFound
from app.models.schemas import (
    ClickIn,
    ErrorResponse,
    GenerateStorefrontRequest,
    GenerateStorefrontResponse,
    StorefrontOut,
    StorefrontStats,
)
from app.services import (
    affiliate,
    destinations,
    extraction,
    instagram,
    storage,
    tiktok,
    transcript,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Creator Storefront API",
    description="Turns a YouTube, TikTok or Instagram travel post into an affiliate hotel storefront.",
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
async def health() -> dict:
    """Liveness, plus enough proxy detail to diagnose a bad deploy.

    Credentials pasted into a host's env UI pick up invisible whitespace, and
    the resulting failure is indistinguishable from a wrong password. Reports
    lengths and a short prefix -- never the secret itself.
    """
    from app.services.transcript import _build_proxy_config

    def describe(value: str) -> dict:
        return {
            "len": len(value),
            "preview": (value[:4] + "..." if len(value) > 4 else value) if value else None,
            "has_whitespace": value != value.strip(),
        }

    proxy: dict = {"configured": config.HAS_PROXY}
    if config.HAS_PROXY:
        if config.WEBSHARE_PROXY_USERNAME:
            proxy["kind"] = "webshare"
            proxy["username"] = describe(config.WEBSHARE_PROXY_USERNAME)
            proxy["password"] = describe(config.WEBSHARE_PROXY_PASSWORD)
        else:
            proxy["kind"] = "generic"
            proxy["http_url"] = describe(config.GENERIC_PROXY_HTTP_URL)
        built = _build_proxy_config()
        url = getattr(built, "url", "") or getattr(built, "http_url", "")
        proxy["endpoint"] = url.split("@", 1)[1] if "@" in url else None

    return {
        "status": "ok",
        "commit": config.GIT_COMMIT,
        "extraction_model": config.EXTRACTION_MODEL,
        "proxy": proxy,
    }


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
    """Video text -> AI extraction -> affiliate links -> Supabase."""
    post = None
    if tiktok.is_tiktok_url(payload.video_url):
        source, platform = tiktok, "tiktok"
        post = tiktok.fetch_post(payload.video_url)
        found = extraction.extract_short_video(post.extraction_document(), post.slides)
    elif instagram.is_instagram_url(payload.video_url):
        source, platform = instagram, "instagram"
        post = instagram.fetch_post(payload.video_url)
        found = extraction.extract_short_video(
            post.extraction_document(),
            post.images,
            platform="Instagram",
            images_kind=post.images_kind,
        )

    if post:
        logger.info("Generating storefront for %s post %s", platform, post.post_id)
        video_url = post.url
        video_title = post.title
        # The post names its own author, so a creator who skips the optional
        # handle field is still credited -- and paid -- as themselves.
        creator_handle = source.normalise_handle(payload.creator_handle) or post.author_handle
        creator_name = payload.creator_name or post.author_name
    else:
        video_id = transcript.parse_video_id(payload.video_url)
        logger.info("Generating storefront for video %s", video_id)
        platform = "youtube"
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_title = transcript.fetch_video_title(video_id)
        found = extraction.extract_travel(transcript.fetch_transcript(video_id))
        creator_handle = payload.creator_handle
        creator_name = payload.creator_name

    # Flights carry the storefront when a video never names where they stayed,
    # so only a video with neither is a dead end.
    if not found.hotels and not found.flights:
        if platform == "tiktok":
            raise NoHotelsFound(
                "No hotels or destinations were named in this TikTok -- not in the "
                "caption, the on-screen text or slides, the tagged location, or what "
                "was said. Try one that names where they stayed."
            )
        if platform == "instagram":
            raise NoHotelsFound(
                "No hotels or destinations were named in this post's caption or "
                "images. Trova can't hear what's said in a Reel, so try one whose "
                "caption or cover names where they stayed."
            )
        raise NoHotelsFound(
            "No hotels or destinations were mentioned in this video. "
            "Try a travel vlog that names where they stayed or where they went."
        )

    # Resolve the creator first: their marker decides who gets paid, so the
    # links cannot be built until we know it.
    creator = storage.upsert_creator(
        creator_name,
        creator_handle,
        payload.travelpayouts_marker,
        platform=platform,
    )
    creator_id = creator["id"]
    creator_marker = (creator.get("travelpayouts_marker") or "").strip()
    base_marker = creator_marker or config.TRAVELPAYOUTS_MARKER

    # Travelpayouts pays one account per marker, so a split cannot happen at
    # the link. Instead the marker carries a SubID naming the creator --
    # "572600.wanderlust" -- and the Performance report breaks earnings down
    # by it, which is what the monthly payout is calculated from.
    creator_subid = (creator.get("subid") or "").strip()
    marker_used = f"{base_marker}.{creator_subid}" if creator_subid else base_marker

    if not creator_marker:
        logger.info(
            "Creator %s billing to platform marker as %s",
            creator_id,
            marker_used,
        )

    # A hotel review narrates no travel, so extraction finds no flights -- but
    # a viewer who wants that hotel still has to get there. Every hotel implies
    # a destination; the airport lookup then decides which are real.
    flights = destinations.merge(
        found.flights, destinations.candidates_from_hotels(found.hotels)
    )

    linked_hotels = affiliate.attach_booking_urls(found.hotels, marker_used)
    linked_flights = affiliate.attach_flight_urls(flights, marker_used)

    thumbnail_url = None
    if post:
        # TikTok's and Instagram's cover links expire within days, so the image
        # is copied rather than linked. Done only now, once the post is known
        # to be worth a storefront.
        cover = source.download_cover(post)
        if cover:
            thumbnail_url = storage.upload_cover(f"{platform}/{post.post_id}", *cover)

    storefront_id = storage.create_storefront(
        creator_id=creator_id,
        video_url=video_url,
        video_title=video_title,
        marker_used=marker_used,
        thumbnail_url=thumbnail_url,
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
        marker_used=marker_used,
        marker_is_creators=bool(creator_marker),
        video_title=video_title,
        hotels_found=len(links),
        flights_found=len(flights),
        storefront=StorefrontOut(
            id=storefront_id,
            creator_id=creator_id,
            video_url=video_url,
            video_title=video_title,
            marker_used=marker_used,
            thumbnail_url=thumbnail_url,
            affiliate_links=links,
            flight_links=flights,
        ),
    )


@app.post("/api/clicks", status_code=204)
async def record_click(
    click: ClickIn, request: Request, background: BackgroundTasks
) -> Response:
    """Record an outbound click from a storefront page.

    Returns immediately and writes in the background: the visitor is already
    on their way to the booking site, and analytics must never delay or block
    that. Reported by the page rather than by routing the link through a
    redirect here, so a booking link never depends on this service being up.
    """
    background.add_task(
        storage.record_click,
        storefront_id=click.storefront_id,
        link_id=click.link_id,
        link_type=click.link_type,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
    )
    return Response(status_code=204)


@app.get("/api/storefronts/{storefront_id}/stats", response_model=StorefrontStats)
async def read_storefront_stats(storefront_id: str) -> StorefrontStats:
    """Click-through numbers for one storefront."""
    return StorefrontStats(**storage.get_storefront_stats(storefront_id))


@app.get(
    "/api/storefronts/{storefront_id}",
    response_model=StorefrontOut,
    responses={404: {"model": ErrorResponse}},
)
async def read_storefront(storefront_id: str) -> StorefrontOut:
    """Public read for the storefront page."""
    return storage.get_storefront(storefront_id)
