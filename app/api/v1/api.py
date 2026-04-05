"""
API v1 router
"""
from fastapi import APIRouter
import logging

# Import active endpoints
from app.api.v1.endpoints import (
    chat, 
    health,
    anomaly,
    token_budget
)

api_router = APIRouter()

# Include active endpoint routers
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(anomaly.router, tags=["anomaly"])
api_router.include_router(token_budget.router, tags=["token-budget"])

# Health check endpoint (duplicate for convenience)
@api_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-assistant-api"}

# Version info
@api_router.get("/version", tags=["info"])
async def get_version():
    """Get API version information"""
    return {
        "version": "1.0.0",
        "api": "v1",
        "status": "active"
    }