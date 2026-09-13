"""Instagram post retrieval: the caption, the images, and who posted it.

A logged-out visitor gets almost nothing from a post's own page, but the embed
version -- the one other websites use to show a post -- still carries the
caption, the author and the images as JSON. That is what this reads.

It cannot hear a Reel. Instagram publishes no caption track the way TikTok
does, so a hotel named only out loud is missed. One written in the caption, on
the cover, or on a carousel slide is found.

Instagram fingerprints the TLS handshake and serves an empty app shell to
anything that does not look like a browser, so requests go through curl_cffi's
Chrome impersonation rather than `requests`.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import RequestException

from app.errors import InvalidVideoUrl, VideoUnavailable
from app.services.transcript import _build_proxy_config

logger = logging.getLogger(__name__)

_EMBED_URL = "https://www.instagram.com/p/{shortcode}/embed/captioned/"
_PAGE_TIMEOUT = 15
_ASSET_TIMEOUT = 10
_IMPERSONATE = "chrome"

_HOSTS = {"instagram.com", "instagr.am"}
# /reel/<code>, /reels/<code>, /p/<code>, /tv/<code>, optionally after a
# username: /wanderlust/reel/<code>. Shortcodes from recent years are 11
# characters; the floor of 10 keeps words like "audio" in /reels/audio/ out.
# /share/reel/<code> is excluded: a share code is not a shortcode, and only
# following its redirect reveals which post it means.
_POST_PATH = re.compile(r"^/(?:(?!share/)[\w.]+/)?(?:reels?|p|tv)/([A-Za-z0-9_-]{10,})(?:/|$)")
_SHARE_PATH = re.compile(r"^/share/(?:[\w]+/)?[A-Za-z0-9_-]+/?$")
_MAX_REDIRECTS = 5

_CONTEXT_JSON = re.compile(r'"contextJSON":("(?:[^"\\]|\\.)*")')

# A carousel can hold 20 images. Each costs ~1,200 input tokens at the size
# chosen below, so this bounds one request's cost and size.
_MAX_IMAGES = 15
# Big enough for the model to read overlaid text, small enough to keep tokens
# and upload size down; Instagram serves several sizes of every image.
_TARGET_WIDTH = 720
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # the API's per-image limit
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")

_TITLE_LIMIT = 90


@dataclass
class InstagramPost:
    post_id: str  # the shortcode
    url: str
    author_handle: str | None
    author_name: str | None
    caption: str = ""
    # For a Reel or single photo, its cover; for a carousel, its slides.
    images: list[tuple[bytes, str]] = field(default_factory=list)
    images_kind: str = "cover"  # "cover" or "slides"
    # Signed and short-lived (days): copy it before storing, never the link.
    cover_url: str | None = None
    title: str = "Instagram post"

    def extraction_document(self) -> str:
        return f"<caption>\n{self.caption}\n</caption>" if self.caption else ""


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
    except ValueError:
        return None
    return host.removeprefix("www.").removeprefix("m."), parsed.path or "/"


def is_instagram_url(url: str) -> bool:
    """True for any instagram.com address, whether or not it names a post."""
    parts = _host_and_path(url)
    return bool(parts) and parts[0] in _HOSTS


def parse_shortcode(url: str) -> str | None:
    """The shortcode a post, Reel or IGTV URL points at, or None."""
    parts = _host_and_path(url)
    if not parts or parts[0] not in _HOSTS:
        return None
    match = _POST_PATH.match(parts[1])
    return match.group(1) if match else None


def _is_share_link(url: str) -> bool:
    parts = _host_and_path(url)
    return bool(parts) and parts[0] in _HOSTS and bool(_SHARE_PATH.match(parts[1]))


def normalise_handle(value: str | None) -> str | None:
    """'@Wanderlust', 'wanderlust ' and '@wanderlust' are one Instagram account."""
    handle = (value or "").strip().lstrip("@").strip().casefold()
    return f"@{handle}" if handle else None


# --- Fetching ----------------------------------------------------------------


def _routes() -> list[dict | None]:
    """Direct first, then the residential proxy when one is configured.

    Two proxy attempts, because each leaves from a different residential IP.
    """
    proxy = _build_proxy_config()
    if proxy is None:
        return [None]
    proxies = dict(proxy.to_requests_dict())
    return [None, proxies, proxies]


def _get(url: str, proxies: dict | None, *, timeout: int, allow_redirects: bool = True):
    return curl_requests.get(
        url,
        impersonate=_IMPERSONATE,
        proxies=proxies,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )


def _resolve_share_link(url: str) -> str:
    """Follow an instagram.com/share/... link to the post it names."""
    redirected = False
    for proxies in _routes():
        current = url
        try:
            for _ in range(_MAX_REDIRECTS):
                response = _get(current, proxies, timeout=_PAGE_TIMEOUT, allow_redirects=False)
                location = response.headers.get("Location")
                if response.status_code not in (301, 302, 303, 307, 308) or not location:
                    break
                redirected = True
                current = urljoin(current, location)
                shortcode = parse_shortcode(current)
                if shortcode:
                    return shortcode
        except RequestException as exc:
            logger.warning("Instagram share link request failed (%s)", type(exc).__name__)
            continue
        if redirected:
            break

    raise VideoUnavailable(
        "Couldn't open that Instagram share link. Open the post, tap Share -> "
        "Copy link, and paste the instagram.com/reel/... link instead."
    )


def _embedded_media(page: str) -> tuple[bool, dict | None]:
    """(served, media) from an embed page.

    `served` is False when Instagram sent no post context at all -- a block,
    not an answer. Served with no media means Instagram answered and would
    not show this post logged-out: private, deleted, or age-restricted.
    """
    if '"contextJSON":null' in (page or ""):
        # The embed page itself, with Instagram saying it has no post to show.
        return True, None
    match = _CONTEXT_JSON.search(page or "")
    if not match:
        return False, None
    try:
        context = json.loads(json.loads(match.group(1)))
    except (ValueError, TypeError):
        return False, None
    media = ((context.get("gql_data") or {}) if isinstance(context, dict) else {}).get("shortcode_media")
    return True, media if isinstance(media, dict) else None


def _load_media(shortcode: str) -> dict:
    # Instagram's "not shown" answer is less explicit than TikTok's, and a
    # rate-limited IP can get it for a perfectly public post. So every route
    # is tried before giving up, and only a unanimous answer blames the post.
    answered = False
    problem = "no attempt made"
    for proxies in _routes():
        route = "proxy" if proxies else "direct"
        try:
            response = _get(_EMBED_URL.format(shortcode=shortcode), proxies, timeout=_PAGE_TIMEOUT)
        except RequestException as exc:
            problem = f"{route}: {type(exc).__name__}"
            logger.warning("Instagram request failed for %s (%s)", shortcode, problem)
            continue

        served, media = _embedded_media(response.text)
        if media:
            logger.info("Read Instagram post %s (%s)", shortcode, route)
            return media
        if served:
            answered = True
            problem = f"{route}: post not shown"
        else:
            problem = f"{route}: HTTP {response.status_code}, no post context"
        logger.warning("Instagram did not return post %s (%s)", shortcode, problem)

    logger.error("Could not read Instagram post %s -- last attempt: %s", shortcode, problem)
    if answered:
        raise VideoUnavailable(
            "Instagram won't show this post to Trova. It may be private, deleted, "
            "age-restricted, or from an account that limits embedding. Try another Reel."
        )
    raise VideoUnavailable(
        "Instagram didn't let Trova read this post just now. Please try again in a minute."
    )


def _best_image_url(node: dict) -> str | None:
    """The smallest size at least _TARGET_WIDTH wide, else the largest there is."""
    resources = [
        res
        for res in (node.get("display_resources") or node.get("thumbnail_resources") or [])
        if isinstance(res, dict) and str(res.get("src") or "").startswith("https://")
    ]
    dimensions = node.get("dimensions") or {}
    if dimensions.get("width") and dimensions.get("height") and dimensions["width"] != dimensions["height"]:
        # Square crops are listed alongside the real aspect ratio, and would
        # cut the text off a portrait cover.
        resources = [r for r in resources if r.get("config_width") != r.get("config_height")] or resources

    by_width = sorted(resources, key=lambda r: int(r.get("config_width") or 0))
    for resource in by_width:
        if int(resource.get("config_width") or 0) >= _TARGET_WIDTH:
            return resource["src"]
    if by_width:
        return by_width[-1]["src"]
    display = node.get("display_url")
    return display if isinstance(display, str) and display.startswith("https://") else None


def _download_image(url: str) -> tuple[bytes, str] | None:
    """One image from Instagram's CDN, or None. Never raises."""
    for proxies in _routes():
        try:
            response = _get(url, proxies, timeout=_ASSET_TIMEOUT)
        except RequestException as exc:
            logger.warning("Instagram image request failed (%s)", type(exc).__name__)
            continue
        content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if response.status_code == 200 and content_type in IMAGE_TYPES and 0 < len(response.content) <= _MAX_IMAGE_BYTES:
            return response.content, content_type
        logger.warning("Skipping Instagram image: HTTP %s, %s, %d bytes", response.status_code, content_type, len(response.content))
    return None


def fetch_post(url: str) -> InstagramPost:
    """Everything readable about one Instagram post.

    Raises `InvalidVideoUrl` for a link that is not a post, and
    `VideoUnavailable` when the post cannot be read.
    """
    shortcode = parse_shortcode(url)
    if shortcode is None:
        if not _is_share_link(url):
            raise InvalidVideoUrl(
                "That Instagram link doesn't point to a post. Open the Reel and copy "
                "its link -- it looks like instagram.com/reel/..."
            )
        shortcode = _resolve_share_link(url)

    media = _load_media(shortcode)

    owner = media.get("owner") if isinstance(media.get("owner"), dict) else {}
    handle = normalise_handle(owner.get("username"))
    edges = ((media.get("edge_media_to_caption") or {}).get("edges") or [])
    caption = str(((edges[0] or {}).get("node") or {}).get("text") or "").strip() if edges else ""

    children = [
        edge.get("node")
        for edge in ((media.get("edge_sidecar_to_children") or {}).get("edges") or [])
        if isinstance(edge, dict) and isinstance(edge.get("node"), dict)
    ]
    cover_url = _best_image_url(media)
    if children:
        image_urls = [u for u in (_best_image_url(child) for child in children[:_MAX_IMAGES]) if u]
        images_kind = "slides"
    else:
        image_urls = [cover_url] if cover_url else []
        images_kind = "cover"

    with ThreadPoolExecutor(max_workers=6) as pool:
        images = [image for image in pool.map(_download_image, image_urls) if image]

    is_reel = media.get("product_type") == "clips"
    post = InstagramPost(
        post_id=shortcode,
        url=f"https://www.instagram.com/{'reel' if is_reel else 'p'}/{shortcode}/",
        author_handle=handle,
        author_name=" ".join(str(owner.get("full_name") or "").split()) or None,
        caption=caption,
        images=images,
        images_kind=images_kind,
        cover_url=cover_url,
        title=_title(caption, handle, is_reel),
    )
    logger.info(
        "Instagram post %s: caption=%d chars, %s images=%d",
        shortcode,
        len(caption),
        images_kind,
        len(images),
    )
    return post


def download_cover(post: InstagramPost) -> tuple[bytes, str] | None:
    """The post's cover image and its content type, or None. Never raises."""
    if post.images_kind == "cover" and post.images:
        return post.images[0]  # already downloaded for extraction
    return _download_image(post.cover_url) if post.cover_url else None


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sentence_end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if sentence_end >= limit // 3:
        return cut[: sentence_end + 1]
    return cut.rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"


def _title(caption: str, handle: str | None, is_reel: bool) -> str:
    """A page headline from the caption's first line, minus tags.

    Instagram captions run long, and the first line is where creators put the
    hook. @mentions are single tokens on Instagram, so a pattern removes them
    cleanly -- unlike TikTok's, which can contain spaces.
    """
    for line in caption.splitlines():
        cleaned = re.sub(r"(?<!\w)[#@][\w.]+", " ", line)
        cleaned = " ".join(cleaned.split()).strip(" .-|")
        if re.search(r"\w", cleaned):
            return _shorten(cleaned, _TITLE_LIMIT)
    kind = "Reel" if is_reel else "post"
    return f"Instagram {kind} by {handle}" if handle else f"Instagram {kind}"
