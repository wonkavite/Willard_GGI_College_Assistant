import os
import secrets

from fastapi import Request, HTTPException, status


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)



def verify_origin(request: Request) -> None:
    """Verify that the request originates from a trusted frontend."""

    trusted_origins = {
        origin.strip()
        for origin in (os.getenv("FRONTEND_ORIGINS")or "").split(",")
        if origin.strip()
    }

    request_origin = request.headers.get("Origin")

    if not request_origin or request_origin not in trusted_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted request origin."
        )

async def verify_csrf_token(request: Request) -> None:
    """Validate the CSRF cookie against the request header."""
    verify_origin(request)
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")

    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing."
        )

    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token."
        )


