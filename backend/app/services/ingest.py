"""
Ingestion Service — parse → chunk → embed → store.

Service Layer pattern: encapsulates business logic for document ingestion.
Depends on OpenAI client (embedding) and VectorStoreRepository (storage).
"""

import logging
import uuid
from typing import List

import pymupdf  # PyMuPDF
from openai import OpenAI

from app.config import Settings
from app.repositories.vector_store import VectorStoreRepository
from app.services.chunker import Chunk, chunk_pages, chunk_text
from app.exceptions import EmptyDocumentError, IngestionError

logger = logging.getLogger(__name__)


class IngestService:
    """
    Handles the full document ingestion pipeline:
        1. Parse file bytes into pages
        2. Chunk pages with overlap + sentence snapping
        3. Batch-embed chunks via OpenAI
        4. Upsert into Qdrant
    """

    def __init__(
        self,
        openai_client: OpenAI,
        vector_store: VectorStoreRepository,
        settings: Settings,
    ):
        self._openai = openai_client
        self._vector_store = vector_store
        self._settings = settings

    # ── Public API ────────────────────────────────────────────────────

    def ingest_file(self, file_bytes: bytes, filename: str) -> dict:
        """
        Full ingestion pipeline for a single file.
        Returns document metadata dict.
        """
        self._vector_store.ensure_collection()

        doc_id = str(uuid.uuid4())
        ext = filename.lower().rsplit(".", 1)[-1]

        pages = self._parse(file_bytes, ext)
        chunks = chunk_pages(
            pages,
            doc_id=doc_id,
            filename=filename,
            settings=self._settings,
        )

        if not chunks:
            raise EmptyDocumentError("No extractable text found in document.")

        try:
            embeddings = self._embed_chunks(chunks)
            self._vector_store.upsert_chunks(chunks, embeddings)
        except Exception as e:
            logger.error("Ingestion pipeline failed for %s: %s", filename, e)
            raise IngestionError(str(e)) from e

        logger.info(
            "Ingested '%s' → %d chunks from %d pages (doc_id=%s)",
            filename, len(chunks), len(pages), doc_id,
        )

        return {
            "doc_id": doc_id,
            "filename": filename,
            "chunks": len(chunks),
            "pages": len(pages),
        }

    def delete_document(self, doc_id: str) -> None:
        """Delete all chunks belonging to a document from the vector store."""
        self._vector_store.delete_by_doc_id(doc_id)

    # ── Private Helpers ───────────────────────────────────────────────

    @staticmethod
    def _parse(file_bytes: bytes, ext: str) -> List[dict]:
        """Route to the appropriate parser based on file extension."""
        if ext == "pdf":
            return IngestService._parse_pdf(file_bytes)
        elif ext in ("txt", "md"):
            return IngestService._parse_txt(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> List[dict]:
        """Extract text per page from PDF bytes."""
        pages = []
        with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    pages.append({"page": i + 1, "text": text})
        return pages

    @staticmethod
    def _parse_txt(file_bytes: bytes) -> List[dict]:
        """Treat plain text / markdown as a single page."""
        text = file_bytes.decode("utf-8", errors="ignore")
        return [{"page": None, "text": text}]

    def _embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        """Batch embed chunk texts using OpenAI embeddings."""
        texts = [c.text for c in chunks]
        batch_size = self._settings.EMBEDDING_BATCH_SIZE
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._openai.embeddings.create(
                model=self._settings.EMBEDDING_MODEL,
                input=batch,
            )
            all_embeddings.extend([r.embedding for r in response.data])

        return all_embeddings
