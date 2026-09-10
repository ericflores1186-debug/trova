"""Domain errors.

Services raise these; `main.py` maps them onto HTTP status codes in one place
so no service needs to import FastAPI.
"""


class AppError(Exception):
    """Base class for expected, user-reportable failures."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidVideoUrl(AppError):
    status_code = 400
    code = "invalid_video_url"


class TranscriptUnavailable(AppError):
    """Subtitles are disabled, missing, or the video is not accessible."""

    status_code = 422
    code = "transcript_unavailable"


class ExtractionFailed(AppError):
    status_code = 502
    code = "extraction_failed"


class NoHotelsFound(AppError):
    status_code = 422
    code = "no_hotels_found"


class StorageFailed(AppError):
    status_code = 500
    code = "storage_failed"


class StorefrontNotFound(AppError):
    status_code = 404
    code = "storefront_not_found"
