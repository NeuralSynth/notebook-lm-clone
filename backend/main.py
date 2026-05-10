"""
FastAPI backend for NotebookLM clone.

Routes:
  POST   /api/upload              — ingest a document
  GET    /api/documents           — list all uploaded documents (in-memory)
  DELETE /api/documents/{doc_id}  — remove a document
  POST   /api/chat                — RAG query, streamed SSE response
  GET    /api/health              — health check
"""

import json
import os
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ingest import ingest_file, delete_document
from query import stream_answer


# ---------------------------------------------------------------------------
# In-memory document registry
# (In production you'd persist this to a DB; fine for assignment scope)
# ---------------------------------------------------------------------------
documents: dict[str, dict] = {}  # doc_id -> {doc_id, filename, chunks, pages}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="NotebookLM Clone API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed = {"pdf", "txt", "md"}
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}. Allowed: pdf, txt, md")

    file_bytes = await file.read()

    if len(file_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large. Max 20MB.")

    try:
        meta = ingest_file(file_bytes, filename=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    documents[meta["doc_id"]] = meta
    return meta


@app.get("/api/documents")
async def list_documents():
    return {"documents": list(documents.values())}


@app.delete("/api/documents/{doc_id}")
async def remove_document(doc_id: str):
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        delete_document(doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")
    del documents[doc_id]
    return {"deleted": doc_id}


class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None  # None = search all docs


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not documents:
        raise HTTPException(status_code=400, detail="No documents uploaded yet.")

    async def event_stream():
        try:
            async for chunk in stream_answer(req.query, doc_ids=req.doc_ids):
                # SSE format
                data = json.dumps({"type": "chunk", "text": chunk})
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
