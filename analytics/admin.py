"""Admin configuration for the analytics app."""

from django.contrib import admin

from .models import ClickEvent


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = [
        "shortened_url",
        "clicked_at",
        "country",
        "city",
        "browser",
        "os",
        "device_type",
    ]
    list_filter = ["device_type", "country", "browser", "os", "clicked_at"]
    search_fields = ["shortened_url__short_code", "ip_address", "country", "city"]
    readonly_fields = [
        "shortened_url",
        "clicked_at",
        "ip_address",
        "country",
        "city",
        "browser",
        "browser_version",
        "os",
        "os_version",
        "device_type",
        "referrer",
        "user_agent",
    ]
    date_hierarchy = "clicked_at"
    ordering = ["-clicked_at"]
