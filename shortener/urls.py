"""URL routing for the shortener app."""

from django.urls import path

from . import views

app_name = "shortener"

urlpatterns = [
    path("", views.home, name="home"),
    path("shorten/", views.shorten, name="shorten"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "dashboard/<str:short_code>/delete/",
        views.delete_url_view,
        name="delete_url",
    ),
    path("accounts/register/", views.register, name="register"),
]
