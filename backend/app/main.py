from app.api.routes import router
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.resources import (
    initialize_resources,
    close_resources
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage shared resources during application lifecycle.
    """

    # Application startup
    print("Starting Willard...")

    await initialize_resources()

    print("Willard startup complete.")

    yield

    # Application shutdown
    print("Shutting down Willard...")

    await close_resources()

    print("Willard shutdown complete.")


app = FastAPI(
    title="Willard - GGI College Information Assistant",
    description="AI-powered college information assistant using RAG.",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Willard API is running!",
        "status": "healthy"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


#.\.venv\Scripts\Activate.ps1
#python -m uvicorn app.main:app --app-dir backend