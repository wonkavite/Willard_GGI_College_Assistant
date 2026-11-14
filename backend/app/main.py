from app.api.routes import chat_router
from contextlib import asynccontextmanager
from app.api.admin_routes import admin_router
from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
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
    print("Starting Wonka...")

    await initialize_resources()

    print("Wonka startup complete.")

    yield

    # Application shutdown
    print("Shutting down Wonka...")

    await close_resources()

    print("Wonka shutdown complete.")


app = FastAPI(
    title="Wonka - GGI College Information Assistant",
    description="AI-powered college information assistant using RAG.",
    version="1.0.0",
    lifespan=lifespan
)

#CORS cofig
origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token"]
)

app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {
        "message": "Wonka API is running!",
        "status": "healthy"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }





#.\.venv\Scripts\Activate.ps1
#python -m uvicorn app.main:app --app-dir backend