"""
FastAPI Dependency Injection — wires services, repos, and config together.

All route handlers use Depends() to receive their dependencies,
making everything testable and decoupled.
"""

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.services.ingest import IngestService
from app.services.query import QueryService


# ── In-memory document registry ──────────────────────────────────────
# (In production, persist this to a database)

documents: dict[str, dict] = {}


def get_document_store() -> dict[str, dict]:
    """Return the in-memory document registry."""
    return documents


# ── Service Providers ─────────────────────────────────────────────────
# Services are created during lifespan and stored in app.state.
# These dependency functions extract them for route injection.

def get_ingest_service(request: Request) -> IngestService:
    """Provide the IngestService from app state."""
    return request.app.state.ingest_service


def get_query_service(request: Request) -> QueryService:
    """Provide the QueryService from app state."""
    return request.app.state.query_service
