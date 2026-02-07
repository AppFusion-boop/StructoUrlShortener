"""Tests for shortener models."""

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from shortener.models import ShortenedURL


@pytest.mark.django_db
class TestShortenedURL:
    def test_create_shortened_url(self):
        url = ShortenedURL.objects.create(
            original_url="https://example.com/very-long-path",
            short_code="abc1234",
        )
        assert url.short_code == "abc1234"
        assert url.original_url == "https://example.com/very-long-path"
        assert url.is_active is True
        assert url.click_count == 0
        assert url.is_custom_code is False

    def test_short_code_unique(self):
        ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="unique1",
        )
        with pytest.raises(Exception):  # IntegrityError  # noqa: B017
            ShortenedURL.objects.create(
                original_url="https://other.com",
                short_code="unique1",
            )

    def test_is_expired_false_when_no_expiry(self):
        url = ShortenedURL(expires_at=None)
        assert url.is_expired is False

    def test_is_expired_true_when_past(self):
        url = ShortenedURL(
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        assert url.is_expired is True

    def test_is_expired_false_when_future(self):
        url = ShortenedURL(
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        assert url.is_expired is False

    def test_str_representation(self):
        url = ShortenedURL(
            original_url="https://example.com/path",
            short_code="test123",
        )
        assert "test123" in str(url)
        assert "example.com" in str(url)

    def test_with_user(self):
        user = User.objects.create_user(username="testuser", password="testpass")
        url = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="user123",
            created_by=user,
        )
        assert url.created_by == user
        assert user.shortened_urls.count() == 1
