import asyncio
import numpy as np

from collections.abc import Mapping
from typing import Any

from app import resources


EMBEDDING_DIMENSION = 384
DEFAULT_BATCH_SIZE = 128

def validate_chunks(chunks: list[Mapping[str, Any]]) -> None:
    """
    Validate the input chunks before embedding generation.
    """

    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Chunks must be a non-empty list.")

    for index, chunk in enumerate(chunks):

        if not isinstance(chunk, Mapping):
            raise TypeError(
                f"Chunk at index {index} must be a mapping."
            )

        content = chunk.get("content")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"Chunk at index {index} has missing or empty content."
            )


async def generate_embeddings(
    chunks: list[Mapping[str, Any]],
    batch_size: int = DEFAULT_BATCH_SIZE
) -> list[np.ndarray]:
    """
    Generate normalized embeddings for document chunks in batches.

    Uses the shared SentenceTransformer instance initialized
    by the FastAPI application.
    """

    # 1. Validate input
    validate_chunks(chunks)

    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError("Batch size must be a positive integer.")

    # 2. Retrieve shared embedding model
    model = resources.embedding_model_instance

    if model is None:
        raise RuntimeError(
            "Embedding model is not initialized. "
            "Initialize application resources first."
        )

    # 3. Extract chunk content
    texts = [chunk["content"] for chunk in chunks]

    embeddings = []

    # 4. Generate embeddings in batches
    for start in range(0, len(texts), batch_size):

        batch_texts = texts[start:start + batch_size]

        batch_embeddings = await asyncio.to_thread(
            model.encode,
            batch_texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        batch_embeddings = np.asarray(batch_embeddings)

        # 5. Validate batch shape
        expected_shape = (len(batch_texts), EMBEDDING_DIMENSION)

        if batch_embeddings.shape != expected_shape:
            raise ValueError(
                f"Invalid embedding shape. "
                f"Expected {expected_shape}, "
                f"received {batch_embeddings.shape}."
            )

        # 6. Validate numerical values
        if not np.isfinite(batch_embeddings).all():
            raise ValueError(
                "Embedding batch contains non-finite values."
            )

        # 7. Validate normalization
        norms = np.linalg.norm(batch_embeddings, axis=1)

        if not np.allclose(norms, 1.0, atol=1e-4):
            raise ValueError(
                "Embedding batch contains vectors that are not normalized."
            )

        embeddings.extend(batch_embeddings)

    # 8. Final count validation
    if len(embeddings) != len(chunks):
        raise RuntimeError(
            "Embedding count does not match the number of input chunks."
        )

    return embeddings