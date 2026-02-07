"""Tests for shortener services."""

import pytest
from django.contrib.auth.models import User

from shortener.models import ShortenedURL
from shortener.services import (
    CodeAlreadyExistsError,
    InvalidCodeError,
    create_short_url,
    deactivate_url,
    get_user_urls,
    increment_click_count,
    resolve_url,
)
from shortener.utils import generate_short_code, is_valid_custom_code


class TestGenerateShortCode:
    def test_default_length(self):
        code = generate_short_code()
        assert len(code) == 7

    def test_custom_length(self):
        code = generate_short_code(10)
        assert len(code) == 10

    def test_no_ambiguous_chars(self):
        for _ in range(100):
            code = generate_short_code()
            for char in "0O1lI":
                assert char not in code

    def test_uniqueness(self):
        codes = {generate_short_code() for _ in range(1000)}
        assert len(codes) == 1000  # All should be unique


class TestIsValidCustomCode:
    def test_valid_codes(self):
        assert is_valid_custom_code("abc") is True
        assert is_valid_custom_code("my-brand") is True
        assert is_valid_custom_code("test123") is True
        assert is_valid_custom_code("a-b-c") is True

    def test_too_short(self):
        assert is_valid_custom_code("ab") is False

    def test_too_long(self):
        assert is_valid_custom_code("a" * 21) is False

    def test_starts_with_hyphen(self):
        assert is_valid_custom_code("-abc") is False

    def test_ends_with_hyphen(self):
        assert is_valid_custom_code("abc-") is False

    def test_special_chars(self):
        assert is_valid_custom_code("ab@c") is False
        assert is_valid_custom_code("ab c") is False


@pytest.mark.django_db
class TestCreateShortUrl:
    def test_create_anonymous(self):
        url = create_short_url("https://example.com")
        assert url.short_code
        assert url.original_url == "https://example.com"
        assert url.created_by is None
        assert url.is_custom_code is False

    def test_create_with_user(self):
        user = User.objects.create_user(username="testuser", password="pass")
        url = create_short_url("https://example.com", user=user)
        assert url.created_by == user

    def test_create_with_custom_code(self):
        user = User.objects.create_user(username="testuser", password="pass")
        url = create_short_url("https://example.com", user=user, custom_code="my-link")
        assert url.short_code == "my-link"
        assert url.is_custom_code is True

    def test_custom_code_already_exists(self):
        user = User.objects.create_user(username="testuser", password="pass")
        create_short_url("https://example.com", user=user, custom_code="taken")
        with pytest.raises(CodeAlreadyExistsError):
            create_short_url("https://other.com", user=user, custom_code="taken")

    def test_invalid_custom_code(self):
        user = User.objects.create_user(username="testuser", password="pass")
        with pytest.raises(InvalidCodeError):
            create_short_url("https://example.com", user=user, custom_code="ab")


@pytest.mark.django_db
class TestResolveUrl:
    def test_resolve_existing(self):
        created = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="resolve1",
        )
        resolved = resolve_url("resolve1")
        assert resolved is not None
        assert resolved.pk == created.pk

    def test_resolve_nonexistent(self):
        assert resolve_url("nonexist") is None

    def test_resolve_inactive(self):
        ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="inactive",
            is_active=False,
        )
        assert resolve_url("inactive") is None


@pytest.mark.django_db
class TestIncrementClickCount:
    def test_increment(self):
        url = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="click1",
        )
        assert url.click_count == 0
        increment_click_count(url)
        url.refresh_from_db()
        assert url.click_count == 1

    def test_multiple_increments(self):
        url = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="click2",
        )
        for _ in range(10):
            increment_click_count(url)
        url.refresh_from_db()
        assert url.click_count == 10


@pytest.mark.django_db
class TestDeactivateUrl:
    def test_deactivate(self):
        url = ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="deact1",
        )
        assert url.is_active is True
        deactivate_url(url)
        url.refresh_from_db()
        assert url.is_active is False


@pytest.mark.django_db
class TestGetUserUrls:
    def test_get_user_urls(self):
        user = User.objects.create_user(username="testuser", password="pass")
        ShortenedURL.objects.create(
            original_url="https://example.com/1",
            short_code="user1a",
            created_by=user,
        )
        ShortenedURL.objects.create(
            original_url="https://example.com/2",
            short_code="user1b",
            created_by=user,
        )
        urls = get_user_urls(user)
        assert urls.count() == 2

    def test_excludes_inactive(self):
        user = User.objects.create_user(username="testuser", password="pass")
        ShortenedURL.objects.create(
            original_url="https://example.com/1",
            short_code="act1",
            created_by=user,
        )
        ShortenedURL.objects.create(
            original_url="https://example.com/2",
            short_code="inact1",
            created_by=user,
            is_active=False,
        )
        urls = get_user_urls(user, active_only=True)
        assert urls.count() == 1
