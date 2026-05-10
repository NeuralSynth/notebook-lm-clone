"""
Application factory — creates and configures the FastAPI app.

Lifespan:
    - Startup: initialize clients, repositories, and services → store in app.state
    - Shutdown: gracefully close external connections

This is the single entry point for uvicorn:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.clients import ClientManager
from app.repositories.vector_store import VectorStoreRepository
from app.services.ingest import IngestService
from app.services.query import QueryService
from app.exceptions import register_exception_handlers
from app.routes import health, documents, chat


def _configure_logging(level: str) -> None:
    """Set up structured logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — runs once at startup and shutdown.

    Startup:
        1. Load settings
        2. Initialize external clients (OpenAI, Qdrant, Gemini)
        3. Create repository and service instances
        4. Store everything in app.state for dependency injection

    Shutdown:
        1. Close external client connections
    """
    settings = get_settings()
    _configure_logging(settings.LOG_LEVEL)

    logger = logging.getLogger(__name__)
    logger.info("Starting %s…", settings.APP_TITLE)

    # Initialize clients
    clients = ClientManager(settings)

    # Initialize repository
    vector_store = VectorStoreRepository(clients.qdrant, settings)

    # Initialize services
    ingest_service = IngestService(clients.openai, vector_store, settings)
    query_service = QueryService(clients.openai, vector_store, settings)

    # Store in app state for dependency injection
    app.state.clients = clients
    app.state.ingest_service = ingest_service
    app.state.query_service = query_service

    logger.info("Application ready.")
    yield

    # Shutdown
    logger.info("Shutting down…")
    clients.close()


def create_app() -> FastAPI:
    """
    Factory function that creates and fully configures the FastAPI app.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_TITLE,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routes ────────────────────────────────────────────────────
    from fastapi.responses import RedirectResponse
    
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(chat.router)

    return app


# Module-level app instance for uvicorn
app = create_app()
