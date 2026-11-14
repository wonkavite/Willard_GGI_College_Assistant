
import asyncio

from fastapi import Request, HTTPException, status
from firebase_admin import auth, exceptions


async def get_current_admin(request: Request):
    """
    Verify the admin's Firebase session cookie.
    """

    session_cookie = request.cookies.get("admin_session")

    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )

    try:
        decoded_token = await asyncio.to_thread(
            auth.verify_session_cookie,
            session_cookie,
            check_revoked=True
        )

        return decoded_token

    except auth.InvalidSessionCookieError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session."
        )

    except auth.UserDisabledError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is disabled."
        )

    except (exceptions.FirebaseError, Exception):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable."
        )
