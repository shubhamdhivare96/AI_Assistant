"""
FastAPI application entry point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exceptions import RequestValidationError as FastAPIValidationError
from pydantic import ValidationError
import logging
from typing import Optional
import uvicorn

from app.config import get_settings

# Get settings instance
settings = get_settings()
# Database removed - using in-memory storage only
# from app.database import engine, Base, get_db
from app.api.v1.api import api_router
# Rate limiter removed - not required for assignment
# from app.middleware.rate_limiter import RateLimiterMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Assistant API",
    description="AI Assistant Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add trusted host middleware
if hasattr(settings, 'ALLOWED_HOSTS'):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Rate limiter removed - not required for assignment
# app.add_middleware(RateLimiterMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("Starting AI Assistant API...")
    
    # Database removed - using in-memory storage only
    # Base.metadata.create_all(bind=engine)
    
    logger.info("AI Assistant API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down AI Assistant API...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "AI Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )