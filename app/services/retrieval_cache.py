"""
Retrieval Caching Service
Caches retrieval results for faster responses
Uses in-memory session cache instead of Redis
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from app.core.session_cache import get_retrieval_cache

logger = logging.getLogger(__name__)

# Use in-memory cache (no Redis dependency)
class RetrievalCache:
    """
    Retrieval Caching Service
    Caches retrieval results to reduce latency and API costs
    Uses in-memory session cache
    """
    
    def __init__(self, ttl: int = 300):
        """
        Initialize cache
        
        Args:
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        self.cache = get_retrieval_cache()
        logger.info("Retrieval cache initialized with in-memory storage")
    
    async def get_cached_results(
        self, 
        query: str, 
        params: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached retrieval results
        
        Returns:
            Cached results or None if not found
        """
        return await self.cache.get_cached_results(query, params)
    
    async def cache_results(
        self, 
        query: str, 
        params: Dict[str, Any], 
        results: List[Dict[str, Any]]
    ):
        """
        Cache retrieval results
        
        Args:
            query: Search query
            params: Parameters used
            results: Results to cache
        """
        await self.cache.cache_results(query, params, results)
    
    async def get_or_retrieve(
        self, 
        query: str, 
        params: Dict[str, Any],
        retrieve_fn: Callable
    ) -> List[Dict[str, Any]]:
        """
        Get from cache or retrieve and cache
        
        Args:
            query: Search query
            params: Parameters
            retrieve_fn: Function to call if cache miss
        
        Returns:
            Retrieval results
        """
        return await self.cache.get_or_retrieve(query, params, retrieve_fn)
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear_cache()
        logger.info("Retrieval cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()
