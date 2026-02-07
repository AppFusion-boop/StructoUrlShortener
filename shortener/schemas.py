"""Pydantic schemas for the URL shortener API."""

from datetime import datetime

from ninja import Schema


class ShortenURLRequest(Schema):
    """Request body for creating a shortened URL."""

    url: str
    custom_code: str | None = None


class ShortenedURLResponse(Schema):
    """Response body for a shortened URL."""

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    click_count: int
    is_custom_code: bool
    qr_code_svg: str | None = None


class URLListResponse(Schema):
    """Response body for listing user's URLs."""

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    click_count: int
    is_active: bool
    is_custom_code: bool


class URLAnalyticsResponse(Schema):
    """Response body for URL analytics."""

    short_code: str
    original_url: str
    total_clicks: int
    unique_visitors: int
    clicks_by_day: list[dict]
    top_countries: list[dict]
    top_browsers: list[dict]
    top_os: list[dict]
    top_devices: list[dict]
    top_referrers: list[dict]


class ErrorResponse(Schema):
    """Standard error response."""

    detail: str


class MessageResponse(Schema):
    """Simple message response."""

    message: str
