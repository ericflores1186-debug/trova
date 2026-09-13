"""TikTok post retrieval: everything a hotel TikTok says, as text.

A TikTok rarely carries its information in one place. The creator might say
the hotel's name out loud, type it on screen, write it in the caption, or tag
the property as the post's location -- and often does only one of those. So
where YouTube needs only a transcript, a TikTok is read from all four.

All four come from the post's own web page, which embeds the full post record
as JSON for TikTok's client-side app. No official API available to Trova
returns spoken captions or on-screen text, so this reads that record directly.
If TikTok restructures the page, `_video_detail` is the place to update.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests

from app.errors import InvalidVideoUrl, VideoUnavailable
from app.services.transcript import _build_proxy_config

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
_PAGE_TIMEOUT = 15
_ASSET_TIMEOUT = 10

_SHARE_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}
_POST_PATH = re.compile(r"^/@([\w.\-]*)/(video|photo)/(\d{15,21})(?:/|$)")
# Older and embedded forms that carry the post ID but not the author.
_ID_ONLY_PATHS = (
    re.compile(r"^/v/(\d{15,21})(?:\.html)?/?$"),
    re.compile(r"^/embed(?:/v2)?/(\d{15,21})/?$"),
    re.compile(r"^/player/v1/(\d{15,21})/?$"),
)
_SHARE_PATH = re.compile(r"^/t/[\w-]+/?$")
_MAX_REDIRECTS = 5

_DATA_SCRIPT = re.compile(
    r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', re.S
)

# Which caption track to read first. Creator-written and auto-transcribed
# tracks are in the words actually spoken; "MT" is a machine translation of
# one of those, so it can garble exactly the proper nouns extraction needs.
_CAPTION_SOURCE_RANK = {"LC": 0, "MU": 0, "ASR": 1}
# A post can run to an hour. Plenty for extraction, and keeps one pathological
# post from producing a request the model cannot take.
_MAX_SPOKEN_CHARS = 100_000

_MAX_COVER_BYTES = 2 * 1024 * 1024
COVER_TYPES = ("image/jpeg", "image/png", "image/webp")

# Each slide costs roughly 1,600 input tokens once the model has resized it,
# and travels base64-encoded inside the extraction request. A hotel carousel
# rarely runs past a dozen slides; this keeps a 35-slide post under the API's
# request size limit.
_MAX_SLIDES = 15
_MAX_SLIDE_BYTES = 5 * 1024 * 1024  # the API's per-image limit
_SLIDE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")

_TITLE_LIMIT = 90


@dataclass(frozen=True)
class PostRef:
    post_id: str
    handle: str = ""  # TikTok resolves /@/video/<id> without it
    kind: str = "video"  # "video" or "photo"

    @property
    def page_url(self) -> str:
        # Always /video/, even for a photo post. TikTok embeds the post record
        # only in /video/ pages; a /photo/ page arrives empty and fills itself
        # in with JavaScript, which is indistinguishable from being blocked.
        return f"https://www.tiktok.com/@{self.handle}/video/{self.post_id}"


@dataclass
class TikTokPost:
    post_id: str
    url: str
    author_handle: str | None
    author_name: str | None
    caption: str = ""
    on_screen_text: list[str] = field(default_factory=list)
    tagged_location: str | None = None
    spoken_words: str = ""
    # A photo post's slides as (image bytes, content type), in order. Slideshow
    # creators often name each hotel only in the text on its slide.
    slides: list[tuple[bytes, str]] = field(default_factory=list)
    # Signed and short-lived: copy it before storing, never store the link.
    cover_url: str | None = None
    title: str = "TikTok video"

    def extraction_document(self) -> str:
        """The post as labelled parts, in the form extraction expects."""
        parts = []
        if self.caption:
            parts.append(f"<caption>\n{self.caption}\n</caption>")
        if self.on_screen_text:
            parts.append("<on_screen_text>\n" + "\n".join(self.on_screen_text) + "\n</on_screen_text>")
        if self.tagged_location:
            parts.append(f"<tagged_location>\n{self.tagged_location}\n</tagged_location>")
        if self.spoken_words:
            parts.append(f"<spoken_words>\n{self.spoken_words}\n</spoken_words>")
        return "\n\n".join(parts)


# --- URLs --------------------------------------------------------------------


def _host_and_path(url: str) -> tuple[str, str] | None:
    candidate = (url or "").strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower()
    except ValueError:  # a malformed port or IPv6 literal
        return None
    return host.removeprefix("www.").removeprefix("m."), parsed.path or "/"


def is_tiktok_url(url: str) -> bool:
    """True for any tiktok.com address, whether or not it names a post."""
    parts = _host_and_path(url)
    return bool(parts) and (parts[0] == "tiktok.com" or parts[0].endswith(".tiktok.com"))


def parse_post_url(url: str) -> PostRef | None:
    """The post a full TikTok URL points at, or None for anything else."""
    parts = _host_and_path(url)
    if not parts or parts[0] != "tiktok.com":
        return None
    path = parts[1]

    match = _POST_PATH.match(path)
    if match:
        return PostRef(post_id=match.group(3), handle=match.group(1), kind=match.group(2))
    for pattern in _ID_ONLY_PATHS:
        match = pattern.match(path)
        if match:
            return PostRef(post_id=match.group(1))
    return None


def _is_share_link(url: str) -> bool:
    parts = _host_and_path(url)
    if not parts:
        return False
    host, path = parts
    if host in _SHARE_HOSTS:
        return path.strip("/") != ""
    return host == "tiktok.com" and bool(_SHARE_PATH.match(path))


def normalise_handle(value: str | None) -> str | None:
    """'@Wanderlust', 'wanderlust ' and '@wanderlust' are one TikTok account."""
    handle = (value or "").strip().lstrip("@").strip().casefold()
    return f"@{handle}" if handle else None


# --- Fetching ----------------------------------------------------------------


def _routes() -> list[dict | None]:
    """Direct first, then the residential proxy when one is configured.

    TikTok serves most requests from anywhere, so the proxy -- metered by the
    gigabyte -- is only spent once a direct request has been refused. Two
    proxy attempts, because each leaves from a different residential IP.
    """
    proxy = _build_proxy_config()
    if proxy is None:
        return [None]
    proxies = dict(proxy.to_requests_dict())
    return [None, proxies, proxies]


def _get(url: str, proxies: dict | None, *, timeout: int, allow_redirects: bool = True) -> requests.Response:
    headers = dict(_HEADERS)
    if proxies:
        # A kept-alive connection would pin every request to one exit IP.
        headers["Connection"] = "close"
    return requests.get(
        url,
        headers=headers,
        proxies=proxies,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )


def _get_asset(url: str, what: str) -> requests.Response | None:
    """Fetch a caption file or image from TikTok's CDN. Never raises."""
    for proxies in _routes():
        try:
            response = _get(url, proxies, timeout=_ASSET_TIMEOUT)
        except requests.RequestException as exc:
            logger.warning("TikTok %s request failed (%s)", what, type(exc).__name__)
            continue
        if response.ok:
            return response
        logger.warning("TikTok %s request returned HTTP %s", what, response.status_code)
    return None


def _resolve_share_link(url: str) -> PostRef:
    """Follow a vm.tiktok.com-style share link to the post it names.

    Links are followed one hop at a time rather than all the way, because the
    first hop already names the post; the page it lands on is fetched later
    with the same fallbacks as any other post.
    """
    redirected = False
    for proxies in _routes():
        current = url
        try:
            for _ in range(_MAX_REDIRECTS):
                response = _get(current, proxies, timeout=_PAGE_TIMEOUT, allow_redirects=False)
                location = response.headers.get("Location")
                if not (response.is_redirect and location):
                    break
                redirected = True
                current = urljoin(current, location)
                ref = parse_post_url(current)
                if ref:
                    return ref
        except requests.RequestException as exc:
            logger.warning("TikTok share link request failed (%s)", type(exc).__name__)
            continue
        if redirected:
            # TikTok answered and sent us somewhere that is not a post --
            # typically its home page, for a deleted video.
            break

    if redirected:
        raise VideoUnavailable(
            "That TikTok share link doesn't lead to a video any more -- it may have "
            "been deleted. Open the video in TikTok, copy its link again, and retry."
        )
    raise VideoUnavailable(
        "Couldn't open that TikTok share link. Open the video in a browser and "
        "paste the full tiktok.com/@name/video/... link instead."
    )


def _video_detail(html: str) -> dict | None:
    """The post record embedded in the page, or None if the page has none.

    None means TikTok did not serve the real page -- a bot check or a block --
    rather than saying anything about the post itself.
    """
    match = _DATA_SCRIPT.search(html or "")
    if not match:
        return None
    try:
        scope = json.loads(match.group(1)).get("__DEFAULT_SCOPE__") or {}
    except (ValueError, AttributeError):
        return None
    detail = scope.get("webapp.video-detail")
    return detail if isinstance(detail, dict) else None


def _load_item(ref: PostRef) -> dict:
    problem = "no attempt made"
    for proxies in _routes():
        route = "proxy" if proxies else "direct"
        try:
            response = _get(ref.page_url, proxies, timeout=_PAGE_TIMEOUT)
        except requests.RequestException as exc:
            problem = f"{route}: {type(exc).__name__}"
            logger.warning("TikTok page request failed for %s (%s)", ref.post_id, problem)
            continue

        detail = _video_detail(response.text)
        if detail is None:
            bot_check = "Please wait..." in response.text or 'id="cs"' in response.text
            problem = f"{route}: HTTP {response.status_code}, {'bot check' if bot_check else 'no post data'}"
            logger.warning("TikTok did not serve post %s (%s)", ref.post_id, problem)
            continue

        item = (detail.get("itemInfo") or {}).get("itemStruct")
        if detail.get("statusCode") in (0, None) and isinstance(item, dict) and item.get("id"):
            logger.info("Read TikTok post %s (%s)", ref.post_id, route)
            return item

        # TikTok served the page and said something about this post: private,
        # deleted, or restricted. Another route will not change that answer.
        logger.info(
            "TikTok post %s unavailable: statusCode=%s %r",
            ref.post_id,
            detail.get("statusCode"),
            detail.get("statusMsg"),
        )
        raise VideoUnavailable(
            "This TikTok is private, deleted or restricted, so Trova can't read it. "
            "Try a public video."
        )

    logger.error("Could not read TikTok post %s -- last attempt: %s", ref.post_id, problem)
    raise VideoUnavailable(
        "TikTok didn't let Trova read this video just now. Please try again in a minute."
    )


def fetch_post(url: str) -> TikTokPost:
    """Everything readable about one TikTok post.

    Raises `InvalidVideoUrl` for a link that is not a post, and
    `VideoUnavailable` when the post cannot be read.
    """
    ref = parse_post_url(url)
    if ref is None:
        if not _is_share_link(url):
            raise InvalidVideoUrl(
                "That TikTok link doesn't point to a video. Open the video and copy "
                "its link -- it looks like tiktok.com/@name/video/..."
            )
        ref = _resolve_share_link(url)

    item = _load_item(ref)

    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    handle = normalise_handle(author.get("uniqueId")) or normalise_handle(ref.handle)
    kind = "photo" if item.get("imagePost") else ref.kind

    post = TikTokPost(
        post_id=ref.post_id,
        url=f"https://www.tiktok.com/{handle or '@'}/{kind}/{ref.post_id}",
        author_handle=handle,
        author_name=" ".join(str(author.get("nickname") or "").split()) or None,
        caption=_caption(item),
        on_screen_text=_on_screen_text(item),
        tagged_location=_tagged_location(item),
        spoken_words=_spoken_words(item),
        slides=_slides(item),
        cover_url=_cover_url(item),
        title=_title(item, handle),
    )
    logger.info(
        "TikTok post %s: caption=%d chars, on-screen=%d, location=%s, spoken=%d chars, slides=%d",
        post.post_id,
        len(post.caption),
        len(post.on_screen_text),
        "yes" if post.tagged_location else "no",
        len(post.spoken_words),
        len(post.slides),
    )
    return post


def download_cover(post: TikTokPost) -> tuple[bytes, str] | None:
    """The post's cover image and its content type, or None. Never raises."""
    if not post.cover_url:
        return None
    response = _get_asset(post.cover_url, "cover")
    if response is None:
        return None
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if content_type not in COVER_TYPES or not 0 < len(response.content) <= _MAX_COVER_BYTES:
        logger.warning(
            "Skipping TikTok cover for %s: %s, %d bytes",
            post.post_id,
            content_type or "no content type",
            len(response.content),
        )
        return None
    return response.content, content_type


# --- Reading the post record -------------------------------------------------


def _collapse(value: object) -> str:
    return " ".join(str(value or "").split())


def _caption(item: dict) -> str:
    caption = str(item.get("desc") or "").strip()
    # A photo post can carry a separate title above its caption.
    image_post = item.get("imagePost") if isinstance(item.get("imagePost"), dict) else {}
    title = _collapse(image_post.get("title"))
    if title and title.casefold() not in caption.casefold():
        caption = f"{title}\n{caption}".strip()
    return caption


def _on_screen_text(item: dict) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for sticker in item.get("stickersOnItem") or []:
        if not isinstance(sticker, dict):
            continue
        for text in sticker.get("stickerText") or []:
            line = _collapse(text)
            if line and line.casefold() not in seen:
                seen.add(line.casefold())
                lines.append(line)
    return lines


def _tagged_location(item: dict) -> str | None:
    """The tagged place, with its type -- "Park MGM Las Vegas (Hotel, Accommodation)".

    The type is what tells extraction a tagged place is a hotel rather than
    the city or shopping street it happens to be on.
    """
    poi = item.get("poi")
    if not isinstance(poi, dict):
        return None
    name = _collapse(poi.get("name"))
    if not name:
        return None

    kinds: list[str] = []
    for key in ("ttTypeNameTiny", "category"):
        kind = _collapse(poi.get(key))
        if kind and kind.casefold() not in (k.casefold() for k in kinds):
            kinds.append(kind)

    label = f"{name} ({', '.join(kinds)})" if kinds else name
    address = _collapse(poi.get("address"))
    return f"{label}, at {address}" if address else label


def _caption_rank(info: dict) -> tuple[int, bool]:
    source = _CAPTION_SOURCE_RANK.get(str(info.get("Source") or "").upper(), 2)
    english = str(info.get("LanguageCodeName") or "").lower().startswith("en")
    return source, not english


def _vtt_text(body: str) -> str:
    spoken: list[str] = []
    for block in re.split(r"\r?\n\s*\r?\n", body.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue  # the WEBVTT header, a NOTE or a STYLE block
        for line in lines[timing + 1 :]:
            text = re.sub(r"<[^>]+>", "", line).strip()
            if text and (not spoken or spoken[-1] != text):
                spoken.append(text)
    return " ".join(spoken)


def _creator_caption_text(body: str) -> str:
    try:
        utterances = json.loads(body).get("utterances") or []
    except (ValueError, AttributeError):
        return ""
    return " ".join(
        _collapse(u.get("text")) for u in utterances if isinstance(u, dict) and _collapse(u.get("text"))
    )


def _spoken_words(item: dict) -> str:
    """The best caption track's text, or "" when the post has none.

    Never raises: the caption, on-screen text and tagged location can still
    carry a storefront without it.
    """
    video = item.get("video") if isinstance(item.get("video"), dict) else {}
    tracks = [
        info
        for info in video.get("subtitleInfos") or []
        if isinstance(info, dict) and str(info.get("Url") or "").startswith("https://")
    ]
    for info in sorted(tracks, key=_caption_rank)[:3]:
        response = _get_asset(info["Url"], "caption")
        if response is None:
            continue
        if str(info.get("Format") or "").lower() == "creator_caption":
            text = _creator_caption_text(response.text)
        else:
            text = _vtt_text(response.text)
        if text:
            return text[:_MAX_SPOKEN_CHARS]
    return ""


def _download_slide(url: str) -> tuple[bytes, str] | None:
    response = _get_asset(url, "slide")
    if response is None:
        return None
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if content_type not in _SLIDE_TYPES or not 0 < len(response.content) <= _MAX_SLIDE_BYTES:
        logger.warning("Skipping TikTok slide: %s, %d bytes", content_type or "no content type", len(response.content))
        return None
    return response.content, content_type


def _slides(item: dict) -> list[tuple[bytes, str]]:
    """A photo post's slide images, in order. [] for a video. Never raises."""
    image_post = item.get("imagePost") if isinstance(item.get("imagePost"), dict) else {}
    urls = []
    for image in image_post.get("images") or []:
        mirrors = ((image or {}).get("imageURL") or {}).get("urlList") or []
        if mirrors and isinstance(mirrors[0], str) and mirrors[0].startswith("https://"):
            urls.append(mirrors[0])
    if len(urls) > _MAX_SLIDES:
        logger.info("Reading the first %d of %d slides", _MAX_SLIDES, len(urls))
        urls = urls[:_MAX_SLIDES]
    if not urls:
        return []

    # In parallel: one at a time, a long carousel would add seconds to every
    # request for no reason. map() keeps the slides in their original order.
    with ThreadPoolExecutor(max_workers=6) as pool:
        downloaded = list(pool.map(_download_slide, urls))
    return [slide for slide in downloaded if slide]


def _cover_url(item: dict) -> str | None:
    video = item.get("video") if isinstance(item.get("video"), dict) else {}
    for key in ("originCover", "cover"):
        value = video.get(key)
        if isinstance(value, str) and value.startswith("https://"):
            return value
    return None


def _without_tags(text: str, text_extra: list) -> str:
    """Cut @mentions and hashtags out of a caption using TikTok's offsets.

    The offsets count UTF-16 code units, as JavaScript does. Applying them to
    a Python string would shift every cut by one per emoji before it, so they
    are applied to the UTF-16 encoding instead.
    """
    units = text.encode("utf-16-le")
    spans = []
    for tag in text_extra:
        if not isinstance(tag, dict) or tag.get("type") not in (0, 1):
            continue
        start, end = tag.get("start"), tag.get("end")
        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(units) // 2:
            spans.append((start, end))

    kept, cursor = [], 0
    for start, end in sorted(spans):
        if start < cursor:
            continue
        kept.append(units[2 * cursor : 2 * start])
        cursor = end
    kept.append(units[2 * cursor :])
    return b"".join(kept).decode("utf-16-le", errors="ignore")


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sentence_end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if sentence_end >= limit // 3:
        return cut[: sentence_end + 1]
    return cut.rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"


def _title(item: dict, handle: str | None) -> str:
    """A page headline in the creator's own words.

    A photo post can have a real title. Otherwise it is the caption minus its
    tags: a TikTok has no title, and its caption is often a run of @mentions
    and hashtags. Built here rather than by the extraction model, which
    derailed when asked to write one.
    """
    image_post = item.get("imagePost") if isinstance(item.get("imagePost"), dict) else {}
    photo_title = _collapse(image_post.get("title"))
    if re.search(r"\w", photo_title):
        return _shorten(photo_title, _TITLE_LIMIT)

    caption = _without_tags(str(item.get("desc") or ""), item.get("textExtra") or [])
    # Catch any hashtag the offsets missed.
    caption = _collapse(re.sub(r"(?<!\w)#[^\s#]+", " ", caption))
    if re.search(r"\w", caption):
        return _shorten(caption, _TITLE_LIMIT)
    for line in _on_screen_text(item):
        if re.search(r"\w", line):
            return _shorten(line, _TITLE_LIMIT)
    return f"TikTok by {handle}" if handle else "TikTok video"
