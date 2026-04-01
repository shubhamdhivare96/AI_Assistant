"""
Connection Pooling Configuration
NOTE: PostgreSQL and Redis removed - using in-memory storage only
Qdrant connection pool retained for vector database
"""
import logging
from qdrant_client import QdrantClient
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Database and Redis removed - using in-memory storage
# def create_db_engine():
#     """Create database engine with connection pooling"""
#     return create_engine(...)

# Qdrant Connection Pool
class QdrantConnectionPool:
    """Connection pool for Qdrant vector database"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections = []
        self.available = []
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        for _ in range(self.max_connections):
            client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=30
            )
            self.connections.append(client)
            self.available.append(client)
        
        logger.info(f"Qdrant connection pool initialized with {self.max_connections} connections")
    
    def get_connection(self) -> QdrantClient:
        """Get connection from pool"""
        if self.available:
            return self.available.pop()
        
        # Pool exhausted, create temporary connection
        logger.warning("Qdrant pool exhausted, creating temporary connection")
        return QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
    
    def return_connection(self, client: QdrantClient):
        """Return connection to pool"""
        if len(self.available) < self.max_connections:
            self.available.append(client)
    
    async def health_check(self) -> dict:
        """Check pool health"""
        return {
            "total_connections": len(self.connections),
            "available_connections": len(self.available),
            "in_use": len(self.connections) - len(self.available),
            "status": "healthy" if self.available else "exhausted"
        }

# Redis removed - using in-memory cache
# def create_redis_pool():
#     """Create Redis connection pool"""
#     return ConnectionPool(...)

# Global instances - lazy initialization
_qdrant_pool = None

def _get_qdrant_pool():
    """Get or create Qdrant connection pool"""
    global _qdrant_pool
    if _qdrant_pool is None:
        _qdrant_pool = QdrantConnectionPool(max_connections=10)
    return _qdrant_pool

# Redis removed - using in-memory cache
# redis_pool = create_redis_pool()
# def get_redis_client() -> Redis:
#     """Get Redis client from pool"""
#     return Redis(connection_pool=redis_pool)

def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client from pool"""
    return _get_qdrant_pool().get_connection()

def return_qdrant_client(client: QdrantClient):
    """Return Qdrant client to pool"""
    _get_qdrant_pool().return_connection(client)
