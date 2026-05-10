"""
Chat route — RAG query with SSE streaming.

Thin HTTP handler that delegates to QueryService.
"""

import json
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_query_service, get_document_store
from app.services.query import QueryService
from app.schemas.models import ChatRequest, ChatChunkEvent, ChatDoneEvent, ChatErrorEvent
from app.exceptions import NoDocumentsError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(
    req: ChatRequest,
    query_service: QueryService = Depends(get_query_service),
    doc_store: dict = Depends(get_document_store),
):
    """Stream a RAG-grounded answer via Server-Sent Events."""
    if not doc_store:
        raise NoDocumentsError("No documents uploaded yet.")

    async def event_stream():
        try:
            async for chunk in query_service.stream_answer(
                req.query, doc_ids=req.doc_ids
            ):
                data = ChatChunkEvent(text=chunk).model_dump_json()
                yield f"data: {data}\n\n"

            yield f"data: {ChatDoneEvent().model_dump_json()}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {ChatErrorEvent(message=str(e)).model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
