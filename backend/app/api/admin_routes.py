
import os
import logging
from pathlib import Path

import httpx
from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    status,
    Depends,
    UploadFile,
    File
)
from pydantic import BaseModel, Field

from app.security.csrf import generate_csrf_token, verify_csrf_token
from app.security.authentication import (
    verify_admin_credentials,
    create_admin_session
)
from app.security.dependencies import get_current_admin

from ingestion.pipeline import ingest_document


logger = logging.getLogger(__name__)

# Router configuration
admin_router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)

# Upload configuration
MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB
SUPPORTED_FORMATS = {".pdf", ".docx", ".txt", ".md"}


def _auth_cookie_options() -> dict:
    is_development = (
        os.getenv("ENVIRONMENT", "production").strip().lower()
        == "development"
    )

    return {
        "secure": not is_development,
        "samesite": "lax" if is_development else "none",
        "path": "/"
    }


# Login Pydantic model
class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


# Admin login endpoint

@admin_router.post("/login")
async def admin_login(credentials: AdminLoginRequest, response: Response):
    auth_stage = "Firebase credential verification"

    try:
        id_token = await verify_admin_credentials(
            credentials.username,
            credentials.password
        )

        auth_stage = "Firebase session creation"

        session_cookie = await create_admin_session(id_token)

        auth_stage = "Session cookie configuration"

        response.set_cookie(
            key="admin_session",
            value=session_cookie,
            httponly=True,
            **_auth_cookie_options()
        )

        csrf_token = generate_csrf_token()

        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            **_auth_cookie_options()
        )

        return {
            "message": "Admin login successful.",
            "csrf_token": csrf_token
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    except httpx.HTTPError:
        logger.exception(
            "Authentication service HTTP error during %s",
            auth_stage
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable."
        )

    except RuntimeError:
        logger.exception(
            "Admin authentication failed during %s",
            auth_stage
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication can not be completed"
        )

# Admin document-upload endpoint
@admin_router.post("/upload")
async def admin_upload(
    file: UploadFile = File(...),
    admin: dict = Depends(get_current_admin),
    _: None = Depends(verify_csrf_token)
):
    filename = Path(file.filename or "").name

    try:
        # Validate filename
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid filename is required."
            )

        # Validate file extension
        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    "Unsupported file type. Only PDF, DOCX, TXT "
                    "and MD files are supported."
                )
            )

        # Read a bounded amount of data to enforce the size limit
        file_bytes = await file.read(MAX_UPLOAD_SIZE + 1)

        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty."
            )

        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds the 15 MB upload limit."
            )

        # Run the existing ingestion pipeline
        result = await ingest_document(file_bytes, filename)

        if result.get("status") != "success":
            logger.warning(
                "Document processing failed for %s: %s",
                filename,
                result.get("status", "unknown")
            )

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded document could not be processed."
            )

        # Return only JSON-serializable information
        return {
            "status": "success",
            "message": "Document uploaded and indexed successfully.",
            "filename": result["filename"],
            "document_id": result["document_id"],
            "total_chunks": result["total_chunks"],
            "total_embeddings": result["total_embeddings"],
            "inserted_objects": result["inserted_objects"]
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Document ingestion failed for %s",
            filename or "unknown file"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Document ingestion failed. Please try again later "
                "or contact the administrator."
            )
        )

    finally:
        await file.close()


# Admin logout endpoint
@admin_router.post("/logout")
async def admin_logout(
    response: Response,
    _: None = Depends(verify_csrf_token)
):
    response.delete_cookie(
        key="admin_session",
        httponly=True,
        **_auth_cookie_options()
    )

    response.delete_cookie(
        key="csrf_token",
        httponly=False,
        **_auth_cookie_options()
    )

    return {"message": "Admin logged out successfully."}


# Get admin session endpoint
@admin_router.get("/session")
async def admin_session(
    request: Request,
    response: Response,
    admin: dict = Depends(get_current_admin)
):
    csrf_token = request.cookies.get("csrf_token")

    if not csrf_token:
        csrf_token = generate_csrf_token()
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            **_auth_cookie_options()
        )

    return {
        "authenticated": True,
        "message": "Admin session is valid.",
        "csrf_token": csrf_token
    }
