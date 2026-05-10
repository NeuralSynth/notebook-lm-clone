"""
Health check route.
"""

from fastapi import APIRouter
from app.schemas.models import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Simple health check endpoint."""
    return HealthResponse()
