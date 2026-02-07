"""Business logic for the URL shortener."""

import io
import logging

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db import IntegrityError
from django.db.models import F

from .models import ShortenedURL
from .utils import generate_short_code, is_valid_custom_code

logger = logging.getLogger(__name__)


class ShortenerError(Exception):
    """Base exception for shortener service errors."""


class InvalidURLError(ShortenerError):
    """Raised when the URL is invalid or unreachable."""


class CodeAlreadyExistsError(ShortenerError):
    """Raised when a custom code already exists."""


class InvalidCodeError(ShortenerError):
    """Raised when a custom code doesn't meet validation rules."""


def create_short_url(
    original_url: str,
    user=None,
    custom_code: str | None = None,
) -> ShortenedURL:
    """Create a shortened URL.

    Args:
        original_url: The URL to shorten.
        user: Optional authenticated user.
        custom_code: Optional user-chosen short code (auth required).

    Returns:
        The created ShortenedURL instance.

    Raises:
        InvalidCodeError: If custom code doesn't meet validation rules.
        CodeAlreadyExistsError: If custom code already exists.
        ShortenerError: If unable to generate a unique code after max retries.
    """
    if custom_code:
        custom_code = custom_code.lower().strip()
        if not is_valid_custom_code(custom_code):
            raise InvalidCodeError(
                "Custom code must be 3-20 characters, alphanumeric and hyphens only, "
                "cannot start or end with a hyphen."
            )
        if ShortenedURL.objects.filter(short_code=custom_code).exists():
            raise CodeAlreadyExistsError(f"The code '{custom_code}' is already taken.")

        return ShortenedURL.objects.create(
            original_url=original_url,
            short_code=custom_code,
            is_custom_code=True,
            created_by=user,
        )

    # Auto-generate a unique short code
    max_retries = settings.SHORTENER_MAX_RETRIES
    code_length = settings.SHORTENER_CODE_LENGTH

    for attempt in range(max_retries):
        # Increase length on retry to reduce collision probability
        length = code_length + attempt
        code = generate_short_code(length)
        try:
            return ShortenedURL.objects.create(
                original_url=original_url,
                short_code=code,
                created_by=user,
            )
        except IntegrityError:
            logger.warning(
                "Short code collision on attempt %d: %s", attempt + 1, code
            )
            continue

    raise ShortenerError(
        "Unable to generate a unique short code. Please try again."
    )


def resolve_url(short_code: str) -> ShortenedURL | None:
    """Look up an active, non-expired shortened URL.

    Returns None if not found, inactive, or expired.
    """
    try:
        url = ShortenedURL.objects.get(short_code=short_code, is_active=True)
    except ShortenedURL.DoesNotExist:
        return None

    if url.is_expired:
        return None

    return url


def increment_click_count(url: ShortenedURL) -> None:
    """Atomically increment the click counter."""
    ShortenedURL.objects.filter(pk=url.pk).update(click_count=F("click_count") + 1)


def deactivate_url(url: ShortenedURL) -> None:
    """Soft-delete a shortened URL."""
    url.is_active = False
    url.save(update_fields=["is_active", "updated_at"])


def get_user_urls(user, active_only: bool = True):
    """Get all shortened URLs for a user."""
    qs = ShortenedURL.objects.filter(created_by=user)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def generate_qr_code_svg(url: str) -> str:
    """Generate an SVG QR code for a URL.

    Returns the QR code as an SVG string.
    """
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10)
    stream = io.BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")
