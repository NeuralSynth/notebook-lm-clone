"""
Query Service — embed → retrieve → generate.

Service Layer pattern: encapsulates the RAG query pipeline.
Depends on unified OpenAI SDK (embedding and generation) and VectorStoreRepository (retrieval).
"""

import json
import logging
from typing import AsyncGenerator, List

from openai import AsyncOpenAI

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
        openai_client: AsyncOpenAI,
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
        current_query = query
        attempts = 0
        max_attempts = self._settings.MAX_REWRITE_ATTEMPTS + 1 if getattr(self._settings, "ENABLE_CRAG", False) else 1
        
        relevant_chunks = []
        while attempts < max_attempts:
            query_vector = await self._embed_query(current_query)
            chunks = await self._vector_store.search(
                query_vector,
                top_k=self._settings.TOP_K,
                doc_ids=doc_ids,
            )
            
            if chunks:
                relevant_chunks = await self._grade_chunks(current_query, chunks)
                if relevant_chunks:
                    break
            
            # No relevant chunks found
            if getattr(self._settings, "ENABLE_CRAG", False) and attempts < getattr(self._settings, "MAX_REWRITE_ATTEMPTS", 0):
                logger.info(f"No relevant chunks found. Rewriting query: '{current_query}'")
                current_query = await self._rewrite_query(current_query)
                logger.info(f"Rewritten query: '{current_query}'")
            
            attempts += 1

        if not relevant_chunks:
            yield "I couldn't find any relevant content in the uploaded documents."
            return

        context = self._build_context(relevant_chunks)
        system = SYSTEM_PROMPT.format(context=context)

        response = await self._openai.chat.completions.create(
            model=self._settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": query}
            ],
            stream=True
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ── Private Helpers ───────────────────────────────────────────────

    async def _embed_query(self, query: str) -> List[float]:
        """Embed a single query string using OpenAI."""
        response = await self._openai.embeddings.create(
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

    async def _grade_chunks(self, query: str, chunks: List[dict]) -> List[dict]:
        """Grade retrieved chunks for relevance to the user query."""
        if not getattr(self._settings, "ENABLE_CRAG", False):
            return chunks

        system_prompt = (
            "You are a relevance grader. You will be provided a user query and a document chunk. "
            "Determine if the chunk contains information relevant to answering the query. "
            "Respond strictly in JSON format with a single boolean field 'relevant'."
        )

        relevant_chunks = []
        for chunk in chunks:
            try:
                response = await self._openai.chat.completions.create(
                    model=self._settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Query: {query}\n\nChunk:\n{chunk['text']}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                result = json.loads(response.choices[0].message.content)
                if result.get("relevant"):
                    relevant_chunks.append(chunk)
            except Exception as e:
                logger.error(f"Error grading chunk: {e}")
                # Default to keeping it if grader fails
                relevant_chunks.append(chunk)

        return relevant_chunks

    async def _rewrite_query(self, query: str) -> str:
        """Rewrite a user query to improve retrieval."""
        system_prompt = (
            "You are a helpful assistant. The user's original query failed to return relevant documents. "
            "Rewrite the query to be a better search string for semantic retrieval. "
            "Remove conversational filler and focus on the core keywords and intent. "
            "Respond strictly in JSON format with a single string field 'rewritten_query'."
        )
        try:
            response = await self._openai.chat.completions.create(
                model=self._settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Original query: {query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("rewritten_query", query)
        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            return query
