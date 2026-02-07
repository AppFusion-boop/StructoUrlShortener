"""URL routing for the analytics app."""

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("<str:short_code>/", views.url_analytics, name="detail"),
]
