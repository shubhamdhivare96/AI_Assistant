"""
Core application modules
"""
from app.core.resilience import resilient_call, CircuitBreaker
# Database and Redis pools removed
# from app.core.connection_pool import get_db_pool, get_qdrant_pool, get_redis_pool
from app.core.connection_pool import get_qdrant_client, return_qdrant_client

__all__ = [
    "resilient_call",
    "CircuitBreaker",
    "get_qdrant_client",
    "return_qdrant_client",
]