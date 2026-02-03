"""
Main API router that aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.endpoints import (
    analytics,
    auth,
    conversations,
    health,
    health_facilities,
    users,
    webhook,
)

api_router = APIRouter()

# Public endpoints
api_router.include_router(health.router)
api_router.include_router(webhook.router)

# Auth endpoints
api_router.include_router(auth.router)

# Protected admin endpoints
api_router.include_router(users.router)
api_router.include_router(conversations.router)
api_router.include_router(analytics.router)
api_router.include_router(health_facilities.router)
