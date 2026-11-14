#This file verify admin credentials and create admin sessions
#importing necessary libraries
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()
import httpx
import asyncio
import firebase_admin
from firebase_admin import auth

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
FIREBASE_ADMIN_EMAIL = os.getenv("FIREBASE_ADMIN_EMAIL")
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

#Lets implement verify admin cred functions

async def verify_admin_credentials(username: str, password: str) -> str:
    """
    Verify shared admin credentials through Firebase Authentication.
    Returns the Firebase ID token on success.
    """

    if not all((ADMIN_USERNAME, FIREBASE_ADMIN_EMAIL, FIREBASE_WEB_API_KEY)):
        raise RuntimeError("Admin authentication is not configured.")

    if not secrets.compare_digest(username, ADMIN_USERNAME):
        raise ValueError("Invalid username or password.")

    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        "accounts:signInWithPassword"
    )

    payload = {
        "email": FIREBASE_ADMIN_EMAIL,
        "password": password,
        "returnSecureToken": True
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            params={"key": FIREBASE_WEB_API_KEY},
            json=payload
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "Invalid response from Firebase Authentication."
        ) from exc

    if response.status_code == 200:
        id_token = data.get("idToken") if isinstance(data, dict) else None

        if not isinstance(id_token, str) or not id_token:
            raise RuntimeError("Firebase did not return a valid ID token.")

        return id_token

    error = data.get("error", {}) if isinstance(data, dict) else {}
    error_code = error.get("message", "") if isinstance(error, dict) else ""

    credential_errors = {
        "INVALID_PASSWORD",
        "EMAIL_NOT_FOUND",
        "INVALID_LOGIN_CREDENTIALS",
        "INVALID_EMAIL",
        "USER_DISABLED"
    }

    configuration_errors = {
        "API_KEY_INVALID",
        "CONFIGURATION_NOT_FOUND",
        "OPERATION_NOT_ALLOWED",
        "PROJECT_NOT_FOUND"
    }

    if error_code in credential_errors:
        raise ValueError("Invalid username or password.")

    if error_code in configuration_errors:
        raise RuntimeError("Firebase authentication configuration failed.")

    if response.status_code == 429 or response.status_code >= 500:
        raise httpx.HTTPStatusError(
            "Firebase Authentication is temporarily unavailable.",
            request=response.request,
            response=response
        )

    raise RuntimeError("Firebase authentication request failed.")


#Creating the admin session
async def create_admin_session(id_token: str) -> str:
    """
    Exchange a Firebase ID token for a session cookie.
    Session validity: 8 hours.
    """

    try:
        session_cookie = await asyncio.to_thread(
            auth.create_session_cookie,
            id_token,
            expires_in=timedelta(hours=8)
        )

        return session_cookie

    except Exception as exc:
        raise RuntimeError("Unable to create admin session.") from exc
