"""Admin configuration for the shortener app."""

from django.contrib import admin

from .models import ShortenedURL


@admin.register(ShortenedURL)
class ShortenedURLAdmin(admin.ModelAdmin):
    list_display = [
        "short_code",
        "original_url_truncated",
        "created_by",
        "click_count",
        "is_active",
        "is_custom_code",
        "created_at",
    ]
    list_filter = ["is_active", "is_custom_code", "created_at"]
    search_fields = ["short_code", "original_url"]
    readonly_fields = ["id", "click_count", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    @admin.display(description="Original URL")
    def original_url_truncated(self, obj):
        if len(obj.original_url) > 80:
            return f"{obj.original_url[:80]}…"
        return obj.original_url
