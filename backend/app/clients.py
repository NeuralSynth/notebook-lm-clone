"""
External client manager — Singleton pattern via FastAPI lifespan.

All third-party clients (OpenAI, Qdrant, Gemini) are created once
at application startup and shared across the entire app lifecycle.
"""

import logging
from openai import OpenAI
from qdrant_client import QdrantClient

from app.config import Settings

logger = logging.getLogger(__name__)


class ClientManager:
    """
    Manages lifecycle of external API clients.

    Created once during FastAPI lifespan startup and stored in app.state.
    All services receive their clients from this manager via dependency injection.
    """

    def __init__(self, settings: Settings):
        logger.info("Initializing external clients…")

        self.openai = OpenAI(
            api_key=settings.API_KEY,
            base_url=settings.API_BASE_URL,
        )
        logger.info("  ✓ API client ready (%s)", settings.API_BASE_URL)

        self.qdrant = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        logger.info("  ✓ Qdrant client ready (%s)", settings.QDRANT_URL)

        self.llm_model_name = settings.LLM_MODEL
        logger.info("  ✓ LLM configured (model: %s)", settings.LLM_MODEL)

    def close(self):
        """Gracefully close clients that support it."""
        try:
            self.qdrant.close()
            logger.info("Qdrant client closed.")
        except Exception:
            pass
