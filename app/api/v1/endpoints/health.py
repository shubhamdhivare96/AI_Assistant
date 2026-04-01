"""
Health check endpoints
"""
from fastapi import APIRouter
from typing import Dict, Any
import logging
import psutil
import os
from datetime import datetime

# Database removed - using in-memory storage
# from app.database import get_db
# from sqlalchemy.orm import Session
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """
    Basic health check - fast startup verification
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-assistant-api",
        "startup": "ready"
    }

@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check with system metrics
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # RAG service health
        rag_health = await check_rag_health()
        
        # LLM service health
        llm_health = await check_llm_health()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            },
            "services": {
                "rag_service": rag_health,
                "llm_service": llm_health
            },
            "version": {
                "api": "1.0.0",
                "python": os.sys.version
            }
        }
        
    except Exception as e:
        logging.error(f"Health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/rag")
async def rag_health_check():
    """
    RAG service health check
    """
    return await check_rag_health()

@router.get("/llm")
async def llm_health_check():
    """
    LLM service health check
    """
    return await check_llm_health()

async def check_rag_health() -> Dict[str, Any]:
    """Check RAG service health"""
    try:
        # Don't create RAGService here as it loads heavy models
        # Just check if we can connect to Qdrant
        from app.core.connection_pool import get_qdrant_client, return_qdrant_client
        
        client = get_qdrant_client()
        collections = client.get_collections()
        return_qdrant_client(client)
        
        return {
            "status": "healthy",
            "vector_database": "connected",
            "collections_count": len(collections.collections)
        }
    except Exception as e:
        logging.error(f"RAG health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_llm_health() -> Dict[str, Any]:
    """Check LLM service health"""
    try:
        llm_service = LLMService()
        
        # Test with a simple prompt
        test_response = await llm_service.generate_response(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.1,
            max_tokens=10
        )
        
        return {
            "status": "healthy",
            "provider": llm_service.settings.LLM_PROVIDER,
            "model": llm_service.settings.LLM_MODEL,
            "test_response": test_response[:50] + "..." if len(test_response) > 50 else test_response
        }
    except Exception as e:
        logging.error(f"LLM health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/metrics")
async def get_metrics():
    """
    Get system and application metrics
    """
    # Process metrics
    process = psutil.Process(os.getpid())
    
    return {
        "process": {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_rss_mb": round(process.memory_info().rss / (1024**2), 2),
            "threads": process.num_threads(),
            "connections": len(process.connections())
        },
        "timestamp": datetime.utcnow().isoformat()
    }