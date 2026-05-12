"""
External client manager — Singleton pattern via FastAPI lifespan.

All third-party clients (OpenAI, Qdrant, Gemini) are created once
at application startup and shared across the entire app lifecycle.
"""

import logging
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

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

        self.openai = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.API_BASE_URL,
        )
        logger.info("  ✓ API client ready (%s)", settings.API_BASE_URL)

        self.qdrant = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        logger.info("  ✓ Qdrant client ready (%s)", settings.QDRANT_URL)

        self.llm_model_name = settings.LLM_MODEL
        logger.info("  ✓ LLM configured (model: %s)", settings.LLM_MODEL)

    async def close(self):
        """Gracefully close clients that support it."""
        try:
            await self.qdrant.close()
            await self.openai.close()
            logger.info("Clients closed.")
        except Exception:
            pass
