"""Models for the URL shortener app."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ShortenedURL(models.Model):
    """A shortened URL mapping."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_url = models.URLField(max_length=2048, db_index=True)
    short_code = models.CharField(max_length=20, unique=True, db_index=True)
    is_custom_code = models.BooleanField(
        default=False,
        help_text="Whether the short code was chosen by the user.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shortened_urls",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date. Null means never expires.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    click_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized click counter for fast reads.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_by", "is_active"]),
            models.Index(fields=["short_code", "is_active"]),
        ]
        verbose_name = "Shortened URL"
        verbose_name_plural = "Shortened URLs"

    def __str__(self) -> str:
        return f"{self.short_code} → {self.original_url[:80]}"

    @property
    def is_expired(self) -> bool:
        """Check if the URL has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() >= self.expires_at

    @property
    def short_url(self) -> str:
        """Return the full short URL."""
        domain = settings.SITE_DOMAIN.rstrip("/")
        return f"{domain}/{self.short_code}"
