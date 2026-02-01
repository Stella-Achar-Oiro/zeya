"""
Health check endpoint for monitoring.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "antenatal-chatbot"}
