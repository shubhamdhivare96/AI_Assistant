"""
API v1 router
"""
from fastapi import APIRouter
import logging

# Import all endpoints
from app.api.v1.endpoints import (
    chat, 
    health,
    documents,
    conversations,
    queries,
    anomaly,
    consent,
    token_budget,
    audit,
    learning
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(queries.router, tags=["queries"])
api_router.include_router(anomaly.router, tags=["anomaly"])
api_router.include_router(consent.router, tags=["consent"])
api_router.include_router(token_budget.router, tags=["token-budget"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(learning.router, tags=["learning"])

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