"""Forms for the URL shortener app."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class ShortenURLForm(forms.Form):
    """Form for shortening a URL."""

    url = forms.URLField(
        max_length=2048,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://example.com/your-long-url",
                "autofocus": True,
            }
        ),
    )
    custom_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "my-custom-code (optional)",
            }
        ),
    )


class RegisterForm(UserCreationForm):
    """User registration form."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class LoginForm(AuthenticationForm):
    """User login form — extends Django's built-in auth form."""

    pass
