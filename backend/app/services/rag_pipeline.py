
from typing import AsyncGenerator

from app.services.hybrid_search import hybrid_chunk_retrieval
from app.services.generation import (
    call_rag_stream,
    SYSTEM_INSTRUCTIONS
)


async def run_rag_pipeline(
    query: str,
    history: list[dict[str, str]] | None = None
) -> AsyncGenerator[str, None]:
    """
    Execute the complete Willard RAG pipeline.

    1. Retrieve relevant institutional chunks.
    2. Pass retrieved chunks to the LLM.
    3. Stream the generated response.
    """

    # 1. Hybrid retrieval
    retrieved_chunks = await hybrid_chunk_retrieval(
        prompt=query,
        limit=5,
        alpha=0.8
    )

    # 2. LLM generation and streaming
    async for response_chunk in call_rag_stream(
        query=query,
        system_instructions=SYSTEM_INSTRUCTIONS,
        retrieved_chunks=retrieved_chunks,
        history=history
    ):
        yield response_chunk
