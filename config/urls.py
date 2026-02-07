"""Root URL configuration for Structo URL Shortener."""

from django.contrib import admin
from django.urls import include, path

from shortener.api import api
from shortener.views import redirect_to_url

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API — django-ninja auto-docs at /api/docs
    path("api/", api.urls),
    # Auth
    path("accounts/", include("django.contrib.auth.urls")),
    # App routes
    path("", include("shortener.urls")),
    path("analytics/", include("analytics.urls")),
    # Short URL redirect — MUST be last (catch-all)
    path("<str:short_code>", redirect_to_url, name="redirect"),
]
