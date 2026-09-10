"""YouTube URL parsing, transcript retrieval, and video title lookup."""

from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, urlparse

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import CouldNotRetrieveTranscript

from app.errors import InvalidVideoUrl, TranscriptUnavailable

logger = logging.getLogger(__name__)

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_PREFIXES = ("/shorts/", "/embed/", "/live/", "/v/")

OEMBED_URL = "https://www.youtube.com/oembed"
_HTTP_TIMEOUT = 10


def parse_video_id(video_url: str) -> str:
    """Extract the 11-character video ID from any common YouTube URL shape.

    Accepts watch URLs, youtu.be short links, /shorts, /embed, /live, and a
    bare video ID.
    """
    candidate = (video_url or "").strip()
    if not candidate:
        raise InvalidVideoUrl("No video URL was provided.")

    if _VIDEO_ID_RE.match(candidate):
        return candidate

    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")

    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host in ("youtube.com", "youtube-nocookie.com"):
        video_id = ""
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            for prefix in _PATH_PREFIXES:
                if parsed.path.startswith(prefix):
                    video_id = parsed.path[len(prefix):].split("/")[0]
                    break
    else:
        raise InvalidVideoUrl(f"'{video_url}' is not a YouTube URL.")

    if not _VIDEO_ID_RE.match(video_id):
        raise InvalidVideoUrl(f"Could not find a YouTube video ID in '{video_url}'.")

    return video_id


def _fetch_snippets(video_id: str) -> list[dict]:
    """Call whichever transcript API the installed version exposes.

    0.6.x ships the `get_transcript` classmethod this project targets; 1.x
    replaced it with an instance-based `fetch()`. Both return per-cue records
    with a `text` field.
    """
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        return YouTubeTranscriptApi.get_transcript(video_id)

    fetched = YouTubeTranscriptApi().fetch(video_id)
    return fetched.to_raw_data()


def fetch_transcript(video_id: str) -> str:
    """Return the video's transcript as one whitespace-normalised string.

    Raises `TranscriptUnavailable` when subtitles are disabled, absent, or the
    video cannot be reached -- the caller turns that into a 422 rather than a
    stack trace.
    """
    try:
        snippets = _fetch_snippets(video_id)
    except CouldNotRetrieveTranscript as exc:
        # Covers TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
        # and the age/region-restricted variants.
        logger.info("No transcript for %s: %s", video_id, type(exc).__name__)
        raise TranscriptUnavailable(
            "This video has no usable transcript. Subtitles may be disabled, "
            "or the video may be private, age-restricted, or region-locked. "
            "Try a video with captions turned on."
        ) from exc
    except Exception as exc:  # network blips, YouTube markup changes
        logger.exception("Transcript fetch failed for %s", video_id)
        raise TranscriptUnavailable(
            "Could not retrieve the transcript for this video. Please try again."
        ) from exc

    text = " ".join(
        (snippet.get("text") or "").strip()
        for snippet in snippets
        if (snippet.get("text") or "").strip()
    )
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise TranscriptUnavailable("The transcript for this video is empty.")

    logger.info("Fetched transcript for %s (%d chars)", video_id, len(text))
    return text


def fetch_video_title(video_id: str) -> str:
    """Best-effort title lookup via YouTube's public oEmbed endpoint.

    Needs no API key. A failure here must not sink the whole request, so it
    falls back to a placeholder.
    """
    try:
        response = requests.get(
            OEMBED_URL,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        title = (response.json().get("title") or "").strip()
        if title:
            return title
    except requests.HTTPError as exc:
        # 404 here just means the video ID does not exist or is private; the
        # transcript fetch below will produce the real, user-facing error.
        status = exc.response.status_code if exc.response is not None else "?"
        logger.info("Title lookup for %s returned HTTP %s", video_id, status)
    except Exception as exc:
        logger.warning("Title lookup failed for %s: %s", video_id, exc)

    return f"YouTube video {video_id}"
