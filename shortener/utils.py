"""Utility functions for the shortener app."""

import secrets
import string

# URL-safe alphabet excluding ambiguous characters (0/O, 1/l/I)
ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"


def generate_short_code(length: int = 7) -> str:
    """Generate a cryptographically secure short code.

    Uses secrets module for cryptographic randomness with a
    URL-safe alphabet that avoids ambiguous characters.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_api_key() -> str:
    """Generate a secure API key for authenticated users."""
    return f"structo_{secrets.token_urlsafe(32)}"


def is_valid_custom_code(code: str) -> bool:
    """Validate a custom short code.

    Rules:
    - 3-20 characters long
    - Only alphanumeric + hyphens
    - Cannot start or end with a hyphen
    """
    if not 3 <= len(code) <= 20:
        return False
    if code.startswith("-") or code.endswith("-"):
        return False
    allowed = set(string.ascii_lowercase + string.digits + "-")
    return all(c in allowed for c in code.lower())
