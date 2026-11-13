
from ingestion.file_processing.file_callings import process_document
from ingestion.chunking.splitter import chunk_document
from ingestion.embeddings.generator import generate_embeddings
from ingestion.weaviate_writer.writer import write_to_weaviate


async def ingest_document(file_bytes: bytes, filename: str) -> dict:
    """
    Execute the complete document ingestion pipeline:
    extraction → chunking → embeddings → Weaviate insertion.
    """

    # 1. Extract document content
    document = process_document(file_bytes, filename)

    if document["status"] != "success":
        return document

    # 2. Split extracted content into chunks
    chunks = chunk_document(document)

    # 3. Generate embeddings
    embeddings = await generate_embeddings(chunks)

    # 4. Insert chunks and embeddings into Weaviate
    response = await write_to_weaviate(chunks, embeddings)

    # 5. Return ingestion result
    return {
        "status": "success",
        "filename": filename,
        "document_id": chunks[0]["document_id"],
        "total_chunks": len(chunks),
        "total_embeddings": len(embeddings),
        "inserted_objects": len(chunks),
        "weaviate_response": response
    }


