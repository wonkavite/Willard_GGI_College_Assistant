
from uuid import UUID

import numpy as np
from weaviate.collections.classes.data import DataObject

from app import resources


async def write_to_weaviate(chunks, embeddings):
    """
    Insert document chunks and their corresponding embeddings
    into the existing Weaviate collection.
    """

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Chunks and embeddings must have the same length."
        )

    client = resources.weaviate_client

    if client is None:
        raise RuntimeError("Weaviate client is not initialized.")

    collection = client.collections.get(
        resources.COLLECTION_NAME
    )

    objects = []

    for chunk, embedding in zip(chunks, embeddings):

        properties = {
            "document_id": chunk["document_id"],
            "document_title": chunk["document_title"],
            "source_url": chunk.get("source_url", ""),
            "source_type": chunk["source_type"],
            "source_group": "uploaded_document",
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"],
            "source_pages": chunk.get("source_pages", []),
            "file_type": chunk["file_type"],
            "extraction_method": chunk["extraction_method"],
            "access_level": "public",
            "privacy_status": "admin_uploaded",
            "content_hash": chunk["content_hash"],
            "chunker_version": chunk["chunker_version"]
        }

        objects.append(
            DataObject(
                uuid=UUID(chunk["chunk_id"]),
                properties=properties,
                vector={
                    "default": np.asarray(embedding).tolist()
                }
            )
        )

    response = await collection.data.insert_many(
        objects=objects
    )

    if response.has_errors:
        raise RuntimeError(
            f"Weaviate insertion encountered errors: {response.errors}"
        )

    return response
