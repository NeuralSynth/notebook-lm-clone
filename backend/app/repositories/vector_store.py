"""
Repository Pattern — Qdrant vector store abstraction.

Encapsulates all Qdrant operations behind a clean interface.
Routes and services never interact with Qdrant directly.
"""

import logging
import uuid
from typing import List

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    PayloadSchemaType,
)

from app.config import Settings
from app.services.chunker import Chunk

logger = logging.getLogger(__name__)


class VectorStoreRepository:
    """
    Abstracts all Qdrant vector database operations.

    Methods:
        ensure_collection() — create collection if missing
        upsert_chunks()     — store embedded chunks
        search()            — similarity search with optional doc filter
        delete_by_doc_id()  — remove all chunks for a document
    """

    def __init__(self, client: AsyncQdrantClient, settings: Settings):
        self._client = client
        self._collection = settings.COLLECTION_NAME
        self._vector_dim = settings.VECTOR_DIM

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't already exist."""
        collections_response = await self._client.get_collections()
        existing = [c.name for c in collections_response.collections]
        if self._collection not in existing:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", self._collection)
        else:
            logger.info("Qdrant collection already exists: %s", self._collection)

        # Always ensure doc_id index exists (required for deletion filters)
        await self._client.create_payload_index(
            collection_name=self._collection,
            field_name="doc_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Ensured payload index on 'doc_id' for collection: %s", self._collection)

    async def upsert_chunks(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> None:
        """Upsert embedded chunks into Qdrant with metadata payloads."""
        points = [
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
            for chunk, vector in zip(chunks, embeddings)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        logger.info("Upserted %d chunks to collection '%s'", len(points), self._collection)

    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        doc_ids: List[str] | None = None,
    ) -> List[dict]:
        """
        Similarity search for top-k chunks.
        If doc_ids is provided, restricts search to those documents.
        """
        search_filter = None
        if doc_ids:
            search_filter = Filter(
                must=[FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))]
            )

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )

        return [
            {
                "text": r.payload["text"],
                "filename": r.payload["filename"],
                "page": r.payload.get("page"),
                "score": r.score,
            }
            for r in results
        ]

    async def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all chunks belonging to a specific document."""
        await self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        logger.info("Deleted chunks for doc_id: %s", doc_id)
