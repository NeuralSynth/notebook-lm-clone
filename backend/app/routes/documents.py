"""
Document routes — upload, list, delete.

Thin HTTP handlers that validate input and delegate to IngestService.
"""

import logging
from fastapi import APIRouter, Depends, File, UploadFile

from app.config import Settings, get_settings
from app.dependencies import get_ingest_service, get_document_store
from app.services.ingest import IngestService
from app.schemas.models import DocumentMeta, DocumentListResponse, DeleteResponse
from app.exceptions import (
    UnsupportedFileTypeError,
    FileTooLargeError,
    DocumentNotFoundError,
    IngestionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/upload", response_model=DocumentMeta)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    ingest_service: IngestService = Depends(get_ingest_service),
    doc_store: dict = Depends(get_document_store),
):
    """Upload and ingest a document (PDF, TXT, or MD)."""
    # Validate file extension
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(ext, settings.ALLOWED_EXTENSIONS)

    # Read file bytes with size guard
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_FILE_SIZE:
        raise FileTooLargeError(len(file_bytes), settings.MAX_FILE_SIZE)

    try:
        meta = await ingest_service.ingest_file(file_bytes, filename=file.filename)
    except (ValueError, Exception) as e:
        raise IngestionError(str(e)) from e

    doc_store[meta["doc_id"]] = meta
    return meta


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    doc_store: dict = Depends(get_document_store),
):
    """List all uploaded documents."""
    return DocumentListResponse(documents=list(doc_store.values()))


@router.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def remove_document(
    doc_id: str,
    ingest_service: IngestService = Depends(get_ingest_service),
    doc_store: dict = Depends(get_document_store),
):
    """Remove a document and its chunks from the vector store."""
    logger.info("Delete request received for doc_id: %s", doc_id)
    if doc_id not in doc_store:
        logger.warning("Document not found in store: %s", doc_id)
        raise DocumentNotFoundError(doc_id)

    try:
        await ingest_service.delete_document(doc_id)
        logger.info("Successfully deleted chunks for doc_id: %s", doc_id)
    except Exception as e:
        logger.error("Failed to delete document %s: %s", doc_id, e)
        raise IngestionError(str(e)) from e

    del doc_store[doc_id]
    logger.info("Removed doc_id %s from memory store.", doc_id)
    return DeleteResponse(deleted=doc_id)
