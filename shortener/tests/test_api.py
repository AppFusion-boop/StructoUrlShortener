"""Tests for the URL shortener API."""

import pytest
from django.contrib.auth.models import User
from django.test import Client

from shortener.models import ShortenedURL


@pytest.mark.django_db
class TestShortenAPI:
    def setup_method(self):
        self.client = Client()

    def test_shorten_url(self):
        response = self.client.post(
            "/api/shorten",
            data={"url": "https://example.com/long-path"},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["original_url"] == "https://example.com/long-path"
        assert data["click_count"] == 0

    def test_shorten_url_with_qr(self):
        response = self.client.post(
            "/api/shorten",
            data={"url": "https://example.com"},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["qr_code_svg"] is not None
        assert "<svg" in data["qr_code_svg"]

    def test_shorten_url_custom_code_requires_auth(self):
        response = self.client.post(
            "/api/shorten",
            data={"url": "https://example.com", "custom_code": "my-code"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_shorten_url_custom_code_authenticated(self):
        User.objects.create_user(username="testuser", password="testpass")
        self.client.login(username="testuser", password="testpass")
        response = self.client.post(
            "/api/shorten",
            data={"url": "https://example.com", "custom_code": "my-code"},
            content_type="application/json",
        )
        assert response.status_code == 201
        assert response.json()["short_code"] == "my-code"

    def test_get_url_info(self):
        ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="info123",
        )
        response = self.client.get("/api/urls/info123")
        assert response.status_code == 200
        assert response.json()["short_code"] == "info123"

    def test_get_url_info_not_found(self):
        response = self.client.get("/api/urls/nonexist")
        assert response.status_code == 404


@pytest.mark.django_db
class TestUserURLsAPI:
    def setup_method(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_list_urls_requires_auth(self):
        response = self.client.get("/api/urls/")
        assert response.status_code == 401

    def test_list_urls_authenticated(self):
        self.client.login(username="testuser", password="testpass")
        ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="list123",
            created_by=self.user,
        )
        response = self.client.get("/api/urls/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["short_code"] == "list123"

    def test_delete_url_authenticated(self):
        self.client.login(username="testuser", password="testpass")
        ShortenedURL.objects.create(
            original_url="https://example.com",
            short_code="del123",
            created_by=self.user,
        )
        response = self.client.delete("/api/urls/del123")
        assert response.status_code == 200
        url = ShortenedURL.objects.get(short_code="del123")
        assert url.is_active is False
