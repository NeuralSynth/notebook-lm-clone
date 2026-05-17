"""
Centralized application configuration using pydantic-settings.

All environment variables and tunable parameters are defined here.
Access via get_settings() which returns a cached singleton.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required env vars:
        OPENAI_API_KEY, GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY

    Optional / tunable:
        All other fields have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── External API Keys ─────────────────────────────────────────────
    API_KEY: str
    API_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    QDRANT_URL: str
    QDRANT_API_KEY: str

    # ── Qdrant ────────────────────────────────────────────────────────
    COLLECTION_NAME: str = "notebooklm"

    # ── Embedding ─────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "text-embedding-004"
    VECTOR_DIM: int = 768  # text-embedding-004 / nomic-embed-text output dimension
    EMBEDDING_BATCH_SIZE: int = 100

    # ── Chunking ──────────────────────────────────────────────────────
    CHUNK_SIZE: int = 2000       # characters (~500 tokens)
    CHUNK_OVERLAP: int = 200     # characters of overlap
    SNAP_WINDOW: int = 100       # sentence-boundary snap window

    # ── RAG ───────────────────────────────────────────────────────────
    TOP_K: int = 6               # chunks to retrieve per query
    LLM_MODEL: str = "gemini-1.5-flash"
    ENABLE_CRAG: bool = True     # enable corrective RAG grading/fallback
    MAX_REWRITE_ATTEMPTS: int = 1 # query rewriting limit

    # ── Upload ────────────────────────────────────────────────────────
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB
    ALLOWED_EXTENSIONS: set[str] = {"pdf", "txt", "md"}

    # ── CORS ──────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── App ───────────────────────────────────────────────────────────
    APP_TITLE: str = "NotebookLM Clone API"
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
