
import asyncio
import weaviate

from app import resources


async def hybrid_chunk_retrieval(prompt, limit=5, alpha=0.8):
    """
    Performs asynchronous hybrid retrieval using the shared
    Weaviate client and SentenceTransformer model.

    Parameters:
        prompt (str): User's search query.
        limit (int): Number of chunks to retrieve.
        alpha (float): Balance between vector and keyword search.

    Returns:
        list: Retrieved chunks with metadata and relevance scores.
    """

    # 1. Retrieve shared initialized resources
    model = resources.embedding_model_instance
    weaviate_client = resources.weaviate_client

    if model is None or weaviate_client is None:
        raise RuntimeError(
            "Resources are not initialized. "
            "Call initialize_resources() first."
        )

    # 2. Generate query embedding without blocking the event loop
    query_vector = await asyncio.to_thread(
        lambda: model.encode(
            prompt,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()
    )

    # 3. Access the existing Weaviate collection
    collection = weaviate_client.collections.get(
        resources.COLLECTION_NAME
    )

    # 4. Perform asynchronous hybrid retrieval
    response = await collection.query.hybrid(
        query=prompt,
        vector=query_vector,
        alpha=alpha,
        limit=limit,
        return_metadata=weaviate.classes.query.MetadataQuery(
            score=True,
            explain_score=True
        )
    )

    # 5. Format retrieved chunks
    results = []

    for obj in response.objects:
        results.append({
            "chunk_id": obj.uuid,
            "score": obj.metadata.score,
            "content": obj.properties.get("content", ""),
            "document_title": obj.properties.get("document_title"),
            "source_url": obj.properties.get("source_url"),
            "source_type": obj.properties.get("source_type"),
            "department": obj.properties.get("department")
        })

    return results

