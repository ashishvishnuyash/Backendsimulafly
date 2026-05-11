"""Google ID token verification.

Verifies the `id_token` issued by Google Sign-In on the client against the
configured set of accepted audience client IDs. Returns the verified
identity payload on success, raises `GoogleAuthError` on any failure.
"""
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import get_settings


class GoogleAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    full_name: str | None
    picture: str | None


_request = google_requests.Request()


def verify_id_token(raw_token: str) -> GoogleIdentity:
    settings = get_settings()
    accepted = settings.GOOGLE_CLIENT_IDS
    if not accepted:
        raise GoogleAuthError("google sign-in is not configured on the server")

    try:
        # When `audience` is a list, google-auth accepts the token if `aud`
        # matches any element. This lets the same backend accept tokens from
        # multiple client IDs (e.g. Android + Web).
        payload = google_id_token.verify_oauth2_token(raw_token, _request, audience=accepted)
    except ValueError as e:
        raise GoogleAuthError(f"invalid google token: {e}") from e

    issuer = payload.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleAuthError("invalid token issuer")

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise GoogleAuthError("token missing required claims (sub/email)")

    if not payload.get("email_verified", False):
        raise GoogleAuthError("google account email is not verified")

    return GoogleIdentity(
        sub=sub,
        email=str(email).lower(),
        email_verified=True,
        full_name=payload.get("name"),
        picture=payload.get("picture"),
    )
