"""Analytics tracking service."""

import logging

from user_agents import parse as parse_ua

from shortener.models import ShortenedURL
from shortener.services import increment_click_count

from .models import ClickEvent

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """Extract the real client IP from the request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def parse_user_agent(ua_string: str) -> dict:
    """Parse a User-Agent string into structured data."""
    if not ua_string:
        return {
            "browser": "",
            "browser_version": "",
            "os": "",
            "os_version": "",
            "device_type": ClickEvent.DeviceType.UNKNOWN,
        }

    ua = parse_ua(ua_string)

    if ua.is_bot:
        device_type = ClickEvent.DeviceType.BOT
    elif ua.is_mobile:
        device_type = ClickEvent.DeviceType.MOBILE
    elif ua.is_tablet:
        device_type = ClickEvent.DeviceType.TABLET
    elif ua.is_pc:
        device_type = ClickEvent.DeviceType.DESKTOP
    else:
        device_type = ClickEvent.DeviceType.UNKNOWN

    return {
        "browser": ua.browser.family or "",
        "browser_version": ua.browser.version_string or "",
        "os": ua.os.family or "",
        "os_version": ua.os.version_string or "",
        "device_type": device_type,
    }


def get_geo_data(ip_address: str) -> dict:
    """Look up geographic data for an IP address.

    Uses Django's built-in GeoIP2 if available; otherwise returns empty data.
    """
    try:
        from django.contrib.gis.geoip2 import GeoIP2

        g = GeoIP2()
        data = g.city(ip_address)
        return {
            "country": (data.get("country_code") or "")[:2],
            "city": (data.get("city") or "")[:100],
        }
    except Exception:
        # GeoIP not configured or IP not found — degrade gracefully
        return {"country": "", "city": ""}


def track_click(request, shortened_url: ShortenedURL) -> ClickEvent:
    """Record a click event for a shortened URL.

    This function:
    1. Extracts client info (IP, User-Agent, referrer)
    2. Parses the User-Agent for browser/OS/device info
    3. Looks up geographic data from IP
    4. Creates a ClickEvent record
    5. Increments the denormalized click counter
    """
    ip_address = get_client_ip(request)
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    referrer = request.META.get("HTTP_REFERER", "")

    # Parse user agent
    ua_data = parse_user_agent(ua_string)

    # Geo lookup (gracefully degrades if not configured)
    geo_data = get_geo_data(ip_address)

    # Create click event
    click = ClickEvent.objects.create(
        shortened_url=shortened_url,
        ip_address=ip_address,
        country=geo_data["country"],
        city=geo_data["city"],
        browser=ua_data["browser"],
        browser_version=ua_data["browser_version"],
        os=ua_data["os"],
        os_version=ua_data["os_version"],
        device_type=ua_data["device_type"],
        referrer=referrer[:2048] if referrer else "",
        user_agent=ua_string,
    )

    # Increment denormalized counter
    increment_click_count(shortened_url)

    return click
