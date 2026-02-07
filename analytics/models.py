"""Models for click analytics tracking."""

from django.db import models


class ClickEvent(models.Model):
    """Records a single click/redirect event."""

    class DeviceType(models.TextChoices):
        MOBILE = "mobile", "Mobile"
        TABLET = "tablet", "Tablet"
        DESKTOP = "desktop", "Desktop"
        BOT = "bot", "Bot"
        UNKNOWN = "unknown", "Unknown"

    shortened_url = models.ForeignKey(
        "shortener.ShortenedURL",
        on_delete=models.CASCADE,
        related_name="clicks",
    )
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=2, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    browser = models.CharField(max_length=50, blank=True, default="")
    browser_version = models.CharField(max_length=20, blank=True, default="")
    os = models.CharField(max_length=50, blank=True, default="")
    os_version = models.CharField(max_length=20, blank=True, default="")
    device_type = models.CharField(
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.UNKNOWN,
    )
    referrer = models.URLField(max_length=2048, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-clicked_at"]
        indexes = [
            models.Index(fields=["shortened_url", "clicked_at"]),
            models.Index(fields=["country"]),
        ]
        verbose_name = "Click Event"
        verbose_name_plural = "Click Events"

    def __str__(self) -> str:
        return f"Click on {self.shortened_url.short_code} at {self.clicked_at}"
