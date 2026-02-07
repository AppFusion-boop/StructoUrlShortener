"""Views for the analytics app."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, render

from shortener.models import ShortenedURL

from .models import ClickEvent


@login_required
def url_analytics(request, short_code: str):
    """Detailed analytics page for a shortened URL."""
    url = get_object_or_404(
        ShortenedURL, short_code=short_code, created_by=request.user
    )

    clicks = ClickEvent.objects.filter(shortened_url=url)
    unique_visitors = clicks.values("ip_address").distinct().count()

    # Aggregations
    clicks_by_day = list(
        clicks.annotate(date=TruncDate("clicked_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    top_countries = list(
        clicks.exclude(country="")
        .values("country")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    top_browsers = list(
        clicks.exclude(browser="")
        .values("browser")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    top_os = list(
        clicks.exclude(os="")
        .values("os")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    top_devices = list(
        clicks.values("device_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_referrers = list(
        clicks.exclude(referrer="")
        .values("referrer")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Prepare chart data as JSON-safe
    import json

    chart_labels = json.dumps(
        [item["date"].strftime("%Y-%m-%d") for item in clicks_by_day]
    )
    chart_data = json.dumps([item["count"] for item in clicks_by_day])

    context = {
        "url": url,
        "unique_visitors": unique_visitors,
        "clicks_by_day": clicks_by_day,
        "top_countries": top_countries,
        "top_browsers": top_browsers,
        "top_os": top_os,
        "top_devices": top_devices,
        "top_referrers": top_referrers,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }
    return render(request, "analytics/detail.html", context)
