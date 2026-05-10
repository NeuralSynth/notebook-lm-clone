"""
Query pipeline: embed → retrieve → generate (streamed via Gemini)
"""

import os
from typing import AsyncGenerator, List

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
import google.generativeai as genai

from ingest import COLLECTION_NAME, EMBEDDING_MODEL, VECTOR_DIM

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
qdrant_client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])


TOP_K = 6  # number of chunks to retrieve


def embed_query(query: str) -> List[float]:
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
    return response.data[0].embedding


def retrieve_chunks(query_vector: List[float], doc_ids: List[str] | None = None) -> List[dict]:
    """
    Search Qdrant for top-k chunks.
    If doc_ids provided, restrict search to those documents.
    """
    search_filter = None
    if doc_ids:
        search_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))]
        )

    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=TOP_K,
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


def build_context(chunks: List[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        page_info = f", page {chunk['page']}" if chunk["page"] else ""
        parts.append(
            f"[Source {i} — {chunk['filename']}{page_info}]\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


SYSTEM_PROMPT = """You are a precise document assistant. A user has uploaded one or more documents and is asking questions about them.

Your rules:
1. Answer ONLY using the provided context below. Do not use your general knowledge.
2. If the answer is not in the context, say: "I couldn't find information about that in the uploaded documents."
3. Always cite your sources — mention the filename and page number when available (e.g. "According to report.pdf, page 3...").
4. Be concise but complete. Use bullet points or structure when it aids clarity.
5. Never fabricate or assume information not present in the context.

Context from documents:
{context}"""


async def stream_answer(query: str, doc_ids: List[str] | None = None) -> AsyncGenerator[str, None]:
    """
    Full RAG query pipeline with streaming response.
    Yields text chunks as they stream from Gemini.
    """
    query_vector = embed_query(query)
    chunks = retrieve_chunks(query_vector, doc_ids=doc_ids)

    if not chunks:
        yield "I couldn't find any relevant content in the uploaded documents."
        return

    context = build_context(chunks)
    system = SYSTEM_PROMPT.format(context=context)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system,
    )

    response = model.generate_content(
        query,
        stream=True,
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text
