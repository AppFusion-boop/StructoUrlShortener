"""Django-Ninja API endpoints for the URL shortener."""

from django.db.models import Count
from django.db.models.functions import TruncDate
from ninja import NinjaAPI, Router
from ninja.security import HttpBearer

from analytics.models import ClickEvent

from .models import ShortenedURL
from .schemas import (
    ErrorResponse,
    MessageResponse,
    ShortenedURLResponse,
    ShortenURLRequest,
    URLAnalyticsResponse,
    URLListResponse,
)
from .services import (
    CodeAlreadyExistsError,
    InvalidCodeError,
    ShortenerError,
    create_short_url,
    deactivate_url,
    generate_qr_code_svg,
    get_user_urls,
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class SessionAuth(HttpBearer):
    """Authenticate via Django session (for web) or Bearer token."""

    def authenticate(self, request, token):
        # For session-based auth (web frontend), check session
        if request.user and request.user.is_authenticated:
            return request.user
        return None


# ---------------------------------------------------------------------------
# API instance
# ---------------------------------------------------------------------------

api = NinjaAPI(
    title="Structo URL Shortener API",
    version="1.0.0",
    description=(
        "A modern, fast URL shortening service. "
        "Shorten URLs, track clicks, and view analytics.\n\n"
        "**Public endpoints** — no auth required:\n"
        "- `POST /api/shorten` — Create a short URL\n"
        "- `GET /api/urls/{short_code}` — Get URL info\n\n"
        "**Authenticated endpoints** — login required:\n"
        "- `GET /api/urls/` — List your URLs\n"
        "- `DELETE /api/urls/{short_code}` — Deactivate a URL\n"
        "- `GET /api/urls/{short_code}/analytics` — View detailed analytics"
    ),
    urls_namespace="api",
)

router = Router()


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/shorten",
    response={201: ShortenedURLResponse, 400: ErrorResponse, 409: ErrorResponse},
    tags=["URLs"],
    summary="Shorten a URL",
    description="Create a shortened URL. Optionally provide a custom code (requires authentication).",
)
def shorten_url(request, payload: ShortenURLRequest):
    """Create a new shortened URL."""
    # Custom codes require authentication
    user = request.user if request.user.is_authenticated else None
    custom_code = payload.custom_code

    if custom_code and not user:
        return 400, {"detail": "Authentication required for custom short codes."}

    try:
        url = create_short_url(
            original_url=payload.url,
            user=user,
            custom_code=custom_code,
        )
    except InvalidCodeError as e:
        return 400, {"detail": str(e)}
    except CodeAlreadyExistsError as e:
        return 409, {"detail": str(e)}
    except ShortenerError as e:
        return 400, {"detail": str(e)}

    qr_svg = generate_qr_code_svg(url.short_url)

    return 201, {
        "short_code": url.short_code,
        "short_url": url.short_url,
        "original_url": url.original_url,
        "created_at": url.created_at,
        "click_count": url.click_count,
        "is_custom_code": url.is_custom_code,
        "qr_code_svg": qr_svg,
    }


@router.get(
    "/urls/{short_code}",
    response={200: ShortenedURLResponse, 404: ErrorResponse},
    tags=["URLs"],
    summary="Get URL info",
    description="Retrieve information about a shortened URL by its code.",
)
def get_url_info(request, short_code: str):
    """Get info about a shortened URL."""
    try:
        url = ShortenedURL.objects.get(short_code=short_code, is_active=True)
    except ShortenedURL.DoesNotExist:
        return 404, {"detail": "URL not found."}

    if url.is_expired:
        return 404, {"detail": "This URL has expired."}

    return {
        "short_code": url.short_code,
        "short_url": url.short_url,
        "original_url": url.original_url,
        "created_at": url.created_at,
        "click_count": url.click_count,
        "is_custom_code": url.is_custom_code,
    }


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/urls/",
    response={200: list[URLListResponse], 401: ErrorResponse},
    tags=["User URLs"],
    summary="List your URLs",
    description="List all shortened URLs created by the authenticated user.",
)
def list_user_urls(request):
    """List all URLs for the authenticated user."""
    if not request.user.is_authenticated:
        return 401, {"detail": "Authentication required."}

    urls = get_user_urls(request.user)
    return [
        {
            "short_code": url.short_code,
            "short_url": url.short_url,
            "original_url": url.original_url,
            "created_at": url.created_at,
            "click_count": url.click_count,
            "is_active": url.is_active,
            "is_custom_code": url.is_custom_code,
        }
        for url in urls
    ]


@router.delete(
    "/urls/{short_code}",
    response={200: MessageResponse, 401: ErrorResponse, 404: ErrorResponse},
    tags=["User URLs"],
    summary="Deactivate a URL",
    description="Soft-delete a shortened URL. Only the owner can deactivate their URLs.",
)
def delete_url(request, short_code: str):
    """Deactivate a shortened URL."""
    if not request.user.is_authenticated:
        return 401, {"detail": "Authentication required."}

    try:
        url = ShortenedURL.objects.get(
            short_code=short_code, created_by=request.user, is_active=True
        )
    except ShortenedURL.DoesNotExist:
        return 404, {"detail": "URL not found or you don't have permission."}

    deactivate_url(url)
    return {"message": "URL deactivated successfully."}


@router.get(
    "/urls/{short_code}/analytics",
    response={200: URLAnalyticsResponse, 401: ErrorResponse, 404: ErrorResponse},
    tags=["Analytics"],
    summary="URL analytics",
    description="Get detailed click analytics for a shortened URL. Requires authentication and ownership.",
)
def get_url_analytics(request, short_code: str):
    """Get detailed analytics for a shortened URL."""
    if not request.user.is_authenticated:
        return 401, {"detail": "Authentication required."}

    try:
        url = ShortenedURL.objects.get(
            short_code=short_code, created_by=request.user
        )
    except ShortenedURL.DoesNotExist:
        return 404, {"detail": "URL not found or you don't have permission."}

    clicks = ClickEvent.objects.filter(shortened_url=url)

    # Clicks by day
    clicks_by_day = list(
        clicks.annotate(date=TruncDate("clicked_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Top countries
    top_countries = list(
        clicks.exclude(country="")
        .values("country")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Top browsers
    top_browsers = list(
        clicks.exclude(browser="")
        .values("browser")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Top OS
    top_os = list(
        clicks.exclude(os="")
        .values("os")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Top devices
    top_devices = list(
        clicks.values("device_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Top referrers
    top_referrers = list(
        clicks.exclude(referrer="")
        .values("referrer")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Unique visitors (by IP)
    unique_visitors = clicks.values("ip_address").distinct().count()

    return {
        "short_code": url.short_code,
        "original_url": url.original_url,
        "total_clicks": url.click_count,
        "unique_visitors": unique_visitors,
        "clicks_by_day": [
            {"date": item["date"].isoformat(), "count": item["count"]}
            for item in clicks_by_day
        ],
        "top_countries": [
            {"name": item["country"], "count": item["count"]}
            for item in top_countries
        ],
        "top_browsers": [
            {"name": item["browser"], "count": item["count"]}
            for item in top_browsers
        ],
        "top_os": [
            {"name": item["os"], "count": item["count"]}
            for item in top_os
        ],
        "top_devices": [
            {"name": item["device_type"], "count": item["count"]}
            for item in top_devices
        ],
        "top_referrers": [
            {"name": item["referrer"], "count": item["count"]}
            for item in top_referrers
        ],
    }


# Register the router
api.add_router("", router)
