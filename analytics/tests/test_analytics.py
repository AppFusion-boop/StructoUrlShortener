"""Tests for analytics services."""

import pytest
from django.test import RequestFactory

from analytics.models import ClickEvent
from analytics.services import get_client_ip, parse_user_agent, track_click
from shortener.models import ShortenedURL


class TestGetClientIP:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_from_remote_addr(self):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        assert get_client_ip(request) == "192.168.1.1"

    def test_from_x_forwarded_for(self):
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 192.168.1.1"
        assert get_client_ip(request) == "10.0.0.1"


class TestParseUserAgent:
    def test_chrome_desktop(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        result = parse_user_agent(ua)
        assert result["browser"] == "Chrome"
        assert result["os"] == "Windows"
        assert result["device_type"] == ClickEvent.DeviceType.DESKTOP

    def test_mobile_safari(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        result = parse_user_agent(ua)
        assert result["browser"] == "Mobile Safari"
        assert result["device_type"] == ClickEvent.DeviceType.MOBILE

    def test_empty_ua(self):
        result = parse_user_agent("")
        assert result["browser"] == ""
        assert result["device_type"] == ClickEvent.DeviceType.UNKNOWN


@pytest.mark.django_db
class TestTrackClick:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_track_click_creates_event(self):
        url = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="track1",
        )
        request = self.factory.get(f"/{url.short_code}")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        request.META["HTTP_REFERER"] = "https://google.com"

        click = track_click(request, url)

        assert click is not None
        assert click.ip_address == "192.168.1.1"
        assert click.referrer == "https://google.com"
        assert ClickEvent.objects.filter(shortened_url=url).count() == 1

        url.refresh_from_db()
        assert url.click_count == 1

    def test_track_click_increments_counter(self):
        url = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="track2",
        )
        request = self.factory.get(f"/{url.short_code}")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        for _ in range(5):
            track_click(request, url)

        url.refresh_from_db()
        assert url.click_count == 5
        assert ClickEvent.objects.filter(shortened_url=url).count() == 5
