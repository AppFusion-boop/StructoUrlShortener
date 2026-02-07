"""Views for the URL shortener app."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from analytics.services import track_click

from .forms import RegisterForm, ShortenURLForm
from .models import ShortenedURL
from .services import (
    CodeAlreadyExistsError,
    InvalidCodeError,
    ShortenerError,
    create_short_url,
    deactivate_url,
    generate_qr_code_svg,
    get_user_urls,
    resolve_url,
)

# ---------------------------------------------------------------------------
# Home / Shorten
# ---------------------------------------------------------------------------


def home(request):
    """Landing page with URL shortening form."""
    form = ShortenURLForm()
    return render(request, "shortener/home.html", {"form": form})


@require_POST
def shorten(request):
    """Handle URL shortening (HTMX partial response)."""
    form = ShortenURLForm(request.POST)
    if not form.is_valid():
        return render(request, "shortener/partials/form_errors.html", {"form": form})

    user = request.user if request.user.is_authenticated else None
    custom_code = form.cleaned_data.get("custom_code") or None

    # Only authenticated users can set custom codes
    if custom_code and not user:
        custom_code = None

    try:
        url = create_short_url(
            original_url=form.cleaned_data["url"],
            user=user,
            custom_code=custom_code,
        )
    except (InvalidCodeError, CodeAlreadyExistsError, ShortenerError) as e:
        return render(
            request,
            "shortener/partials/form_errors.html",
            {"error_message": str(e)},
        )

    qr_svg = generate_qr_code_svg(url.short_url)

    return render(
        request,
        "shortener/partials/result.html",
        {
            "url": url,
            "qr_svg": qr_svg,
        },
    )


# ---------------------------------------------------------------------------
# Redirect
# ---------------------------------------------------------------------------


@require_GET
def redirect_to_url(request, short_code: str):
    """Resolve a short code and redirect to the original URL."""
    url = resolve_url(short_code)
    if url is None:
        raise Http404("Short URL not found or has expired.")

    # Track the click asynchronously
    track_click(request, url)

    return redirect(url.original_url, permanent=False)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@login_required
def dashboard(request):
    """User dashboard showing their shortened URLs."""
    urls = get_user_urls(request.user)
    return render(request, "shortener/dashboard.html", {"urls": urls})


@login_required
@require_http_methods(["DELETE"])
def delete_url_view(request, short_code: str):
    """HTMX-powered URL deletion."""
    url = get_object_or_404(
        ShortenedURL, short_code=short_code, created_by=request.user, is_active=True
    )
    deactivate_url(url)
    return HttpResponse("")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def register(request):
    """User registration view."""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("shortener:dashboard")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})
