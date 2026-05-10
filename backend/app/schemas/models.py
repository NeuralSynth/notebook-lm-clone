"""
Pydantic models for API request/response contracts.

Keeps all data shapes in one place so routes stay thin.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Body for POST /api/chat."""
    query: str = Field(..., min_length=1, description="User question")
    doc_ids: Optional[List[str]] = Field(
        default=None,
        description="Restrict search to these document IDs. None = search all.",
    )


# ── Responses ─────────────────────────────────────────────────────────

class DocumentMeta(BaseModel):
    """Metadata returned after ingestion / in document list."""
    doc_id: str
    filename: str
    chunks: int
    pages: int


class DocumentListResponse(BaseModel):
    """Response for GET /api/documents."""
    documents: List[DocumentMeta]


class DeleteResponse(BaseModel):
    """Response for DELETE /api/documents/{doc_id}."""
    deleted: str


class HealthResponse(BaseModel):
    """Response for GET /api/health."""
    status: str = "ok"


# ── SSE Event Types ───────────────────────────────────────────────────

class ChatChunkEvent(BaseModel):
    """Streamed text chunk."""
    type: str = "chunk"
    text: str


class ChatDoneEvent(BaseModel):
    """Stream completion signal."""
    type: str = "done"


class ChatErrorEvent(BaseModel):
    """Stream error signal."""
    type: str = "error"
    message: str
