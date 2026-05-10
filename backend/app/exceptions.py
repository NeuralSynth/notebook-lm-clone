"""
Custom exceptions and global FastAPI exception handlers.

Provides domain-specific exceptions that are caught by handlers
registered on the app, keeping route code clean.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ── Domain Exceptions ─────────────────────────────────────────────────

class DocumentNotFoundError(Exception):
    """Raised when a document ID is not in the registry."""
    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        super().__init__(f"Document not found: {doc_id}")


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file has a disallowed extension."""
    def __init__(self, ext: str, allowed: set[str]):
        self.ext = ext
        self.allowed = allowed
        super().__init__(
            f"Unsupported file type: .{ext}. Allowed: {', '.join(sorted(allowed))}"
        )


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the size limit."""
    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"File too large ({size / 1024 / 1024:.1f}MB). Max: {max_size / 1024 / 1024:.0f}MB."
        )


class EmptyDocumentError(Exception):
    """Raised when a document yields no extractable text."""
    pass


class IngestionError(Exception):
    """Raised when the ingestion pipeline fails."""
    pass


class NoDocumentsError(Exception):
    """Raised when chat is attempted with no documents uploaded."""
    pass


# ── Handler Registration ─────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(DocumentNotFoundError)
    async def _document_not_found(request: Request, exc: DocumentNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UnsupportedFileTypeError)
    async def _unsupported_file(request: Request, exc: UnsupportedFileTypeError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(FileTooLargeError)
    async def _file_too_large(request: Request, exc: FileTooLargeError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(EmptyDocumentError)
    async def _empty_document(request: Request, exc: EmptyDocumentError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(NoDocumentsError)
    async def _no_documents(request: Request, exc: NoDocumentsError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(IngestionError)
    async def _ingestion_error(request: Request, exc: IngestionError):
        logger.error("Ingestion failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Ingestion failed: {str(exc)}"},
        )
