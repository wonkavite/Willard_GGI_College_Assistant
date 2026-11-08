
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

from app.services.rag_pipeline import run_rag_pipeline


router = APIRouter(
    prefix="/api",
    tags=["Chat"]
)


# ============================================================
# CHAT REQUEST SCHEMA
# ============================================================

class ChatRequest(BaseModel):
    user_id: UUID
    query: str = Field(min_length=1, max_length=5000)
    history: list[dict[str, str]] = Field(default_factory=list)


# ============================================================
# CHAT ENDPOINT
# ============================================================

@router.post("/chat")
async def chat(request: ChatRequest):

    async def response_stream():
        async for chunk in run_rag_pipeline(
            query=request.query
        ):
            yield chunk

    return StreamingResponse(
        response_stream(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
