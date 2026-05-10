"""
Query Service — embed → retrieve → generate.

Service Layer pattern: encapsulates the RAG query pipeline.
Depends on unified OpenAI SDK (embedding and generation) and VectorStoreRepository (retrieval).
"""

import logging
from typing import AsyncGenerator, List

from openai import OpenAI

from app.config import Settings
from app.repositories.vector_store import VectorStoreRepository

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a precise document assistant. A user has uploaded one or more documents and is asking questions about them.

Your rules:
1. Answer ONLY using the provided context below. Do not use your general knowledge.
2. If the answer is not in the context, say: "I couldn't find information about that in the uploaded documents."
3. Always cite your sources — mention the filename and page number when available (e.g. "According to report.pdf, page 3...").
4. Be concise but complete. Use bullet points or structure when it aids clarity.
5. Never fabricate or assume information not present in the context.

Context from documents:
{context}"""


class QueryService:
    """
    Handles the full RAG query pipeline:
        1. Embed the user query
        2. Retrieve top-k chunks from vector store
        3. Build grounded context with citations
        4. Stream response via Gemini
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

    async def stream_answer(
        self,
        query: str,
        doc_ids: List[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Full RAG query pipeline with streaming response.
        Yields text chunks as they stream from Gemini.
        """
        query_vector = self._embed_query(query)
        chunks = self._vector_store.search(
            query_vector,
            top_k=self._settings.TOP_K,
            doc_ids=doc_ids,
        )

        if not chunks:
            yield "I couldn't find any relevant content in the uploaded documents."
            return

        context = self._build_context(chunks)
        system = SYSTEM_PROMPT.format(context=context)

        response = self._openai.chat.completions.create(
            model=self._settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query}
            ],
            stream=True
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ── Private Helpers ───────────────────────────────────────────────

    def _embed_query(self, query: str) -> List[float]:
        """Embed a single query string using OpenAI."""
        response = self._openai.embeddings.create(
            model=self._settings.EMBEDDING_MODEL,
            input=[query],
        )
        return response.data[0].embedding

    @staticmethod
    def _build_context(chunks: List[dict]) -> str:
        """Format retrieved chunks into a citation-aware context string."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            page_info = f", page {chunk['page']}" if chunk["page"] else ""
            parts.append(
                f"[Source {i} — {chunk['filename']}{page_info}]\n{chunk['text']}"
            )
        return "\n\n---\n\n".join(parts)
