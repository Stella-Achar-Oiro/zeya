"""
Health check endpoint for monitoring.
"""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Health check that verifies database and Redis connectivity."""
    checks = {"service": "antenatal-chatbot"}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Health check: database failed - %s", e)
        checks["database"] = "error"

    # Redis check
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error("Health check: redis failed - %s", e)
        checks["redis"] = "error"

    all_ok = checks.get("database") == "ok" and checks.get("redis") == "ok"
    checks["status"] = "healthy" if all_ok else "degraded"

    return checks
