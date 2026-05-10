"""
Ingestion pipeline: parse → chunk → embed → upsert to Qdrant
"""

import os
import uuid
import io
from typing import List

import pymupdf  # PyMuPDF
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

from chunker import Chunk, chunk_pages, chunk_text

COLLECTION_NAME = "notebooklm"
EMBEDDING_MODEL = "text-embedding-3-large"
VECTOR_DIM = 3072  # text-embedding-3-large output dim

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
qdrant_client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)


def ensure_collection():
    """Create Qdrant collection if it doesn't exist."""
    existing = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


def parse_pdf(file_bytes: bytes) -> List[dict]:
    """Extract text per page from PDF bytes."""
    pages = []
    with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append({"page": i + 1, "text": text})
    return pages


def parse_txt(file_bytes: bytes) -> List[dict]:
    """Treat plain text as a single page."""
    text = file_bytes.decode("utf-8", errors="ignore")
    return [{"page": None, "text": text}]


def embed_chunks(chunks: List[Chunk]) -> List[List[float]]:
    """Batch embed chunk texts using OpenAI embeddings."""
    texts = [c.text for c in chunks]
    # OpenAI allows up to 2048 texts per request; batch just in case
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        all_embeddings.extend([r.embedding for r in response.data])
    return all_embeddings


def upsert_chunks(chunks: List[Chunk], embeddings: List[List[float]]):
    """Upsert embedded chunks into Qdrant."""
    points = []
    for chunk, vector in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": chunk.text,
                    "doc_id": chunk.doc_id,
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "page": chunk.page,
                },
            )
        )
    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)


def ingest_file(file_bytes: bytes, filename: str) -> dict:
    """
    Full ingestion pipeline for a single file.
    Returns doc metadata.
    """
    ensure_collection()

    doc_id = str(uuid.uuid4())
    ext = filename.lower().rsplit(".", 1)[-1]

    if ext == "pdf":
        pages = parse_pdf(file_bytes)
    elif ext in ("txt", "md"):
        pages = parse_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    chunks = chunk_pages(pages, doc_id=doc_id, filename=filename)

    if not chunks:
        raise ValueError("No extractable text found in document.")

    embeddings = embed_chunks(chunks)
    upsert_chunks(chunks, embeddings)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "chunks": len(chunks),
        "pages": len(pages),
    }


def delete_document(doc_id: str):
    """Delete all chunks belonging to a document from Qdrant."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    qdrant_client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
