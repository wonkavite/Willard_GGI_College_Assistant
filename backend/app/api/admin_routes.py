#We are defining the admin route
import os
from app.security.csrf import generate_csrf_token, verify_csrf_token
from fastapi import APIRouter, HTTPException, Response, status,Depends
from pydantic import BaseModel, Field
import httpx
from app.security.authentication import (
    verify_admin_credentials,
    create_admin_session
)
from app.security.dependencies import get_current_admin

#creating thye router
admin_router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)

#Login pydantic model
class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


#Admin login endpoint
@admin_router.post("/login")
async def admin_login(
    credentials: AdminLoginRequest,
    response: Response
):
    try:
        id_token = await verify_admin_credentials(
            credentials.username,
            credentials.password
        )

        session_cookie = await create_admin_session(id_token)

        response.set_cookie(
            key="admin_session",
            value=session_cookie,
            httponly=True,
            secure=os.getenv("ENVIRONMENT", "production").strip().lower() != "development",
            samesite="lax",
            path="/"
        )

        csrf_token = generate_csrf_token()

        response.set_cookie(
             key="csrf_token",
             value=csrf_token,
             httponly=False,
              secure=os.getenv("ENVIRONMENT", "production").strip().lower() != "development",
             samesite="lax",
              path="/"
)

        return {"message": "Admin login successful."}

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable."
        )

    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication can not be completed"
        )
#admin logout endpoint
@admin_router.post("/logout")
async def admin_logout(
    response: Response,
    _: None = Depends(verify_csrf_token)
):
    response.delete_cookie(
        key="admin_session",
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "production").strip().lower() != "development",
        samesite="lax",
        path="/"
    )

    response.delete_cookie(
        key="csrf_token",
        httponly=False,
        secure=os.getenv("ENVIRONMENT", "production").strip().lower() != "development",
        samesite="lax",
        path="/"
    )

    return {"message": "Admin logged out successfully."}

#Get session endpoint
@admin_router.get("/session")
async def admin_session(
    admin: dict = Depends(get_current_admin)
):
    return {
        "authenticated": True,
        "message": "Admin session is valid."
    }