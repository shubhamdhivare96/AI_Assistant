"""
In-Memory Session Cache
Replaces Redis for retrieval caching and session management
"""
import logging
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class SessionCache:
    """
    In-memory cache with TTL support
    Thread-safe implementation using OrderedDict for LRU eviction
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize session cache
        
        Args:
            max_size: Maximum number of cached items
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.lock = Lock()
        logger.info(f"Session cache initialized (max_size={max_size}, ttl={default_ttl}s)")
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired"""
        return time.time() - timestamp > self.default_ttl
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.default_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    def _evict_lru(self):
        """Evict least recently used item if cache is full"""
        if len(self.cache) >= self.max_size:
            # Remove oldest item (first in OrderedDict)
            evicted_key = next(iter(self.cache))
            del self.cache[evicted_key]
            logger.debug(f"Evicted LRU entry: {evicted_key}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                
                # Check if expired
                if self._is_expired(timestamp):
                    del self.cache[key]
                    logger.debug(f"Cache MISS (expired): {key}")
                    return None
                
                # Move to end (mark as recently used)
                self.cache.move_to_end(key)
                logger.debug(f"Cache HIT: {key}")
                return value
            
            logger.debug(f"Cache MISS: {key}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL (uses default if not provided)
        """
        with self.lock:
            # Cleanup expired entries periodically
            if len(self.cache) % 100 == 0:
                self._cleanup_expired()
            
            # Evict LRU if needed
            self._evict_lru()
            
            # Store with timestamp
            self.cache[key] = (value, time.time())
            self.cache.move_to_end(key)
            logger.debug(f"Cache SET: {key}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache DELETE: {key}")
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_entries = len(self.cache)
            current_time = time.time()
            expired_count = sum(
                1 for _, timestamp in self.cache.values()
                if current_time - timestamp > self.default_ttl
            )
            
            return {
                "cache_type": "in-memory",
                "total_entries": total_entries,
                "active_entries": total_entries - expired_count,
                "expired_entries": expired_count,
                "max_size": self.max_size,
                "ttl_seconds": self.default_ttl
            }


class RetrievalCache:
    """
    Specialized cache for retrieval results
    Uses SessionCache internally with query-specific key generation
    """
    
    def __init__(self, session_cache: SessionCache):
        """
        Initialize retrieval cache
        
        Args:
            session_cache: Underlying session cache instance
        """
        self.cache = session_cache
        logger.info("Retrieval cache initialized")
    
    def _generate_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from query and parameters
        
        Args:
            query: Search query
            params: Additional parameters (top_k, etc.)
        
        Returns:
            Cache key string
        """
        # Create deterministic string from query and params
        cache_input = f"{query}:{json.dumps(params, sort_keys=True)}"
        
        # Hash to create key
        key_hash = hashlib.md5(cache_input.encode()).hexdigest()
        
        return f"retrieval:{key_hash}"
    
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
        cache_key = self._generate_cache_key(query, params)
        cached = self.cache.get(cache_key)
        
        if cached:
            logger.info(f"Retrieval cache HIT: {query[:50]}")
            return cached
        
        logger.info(f"Retrieval cache MISS: {query[:50]}")
        return None
    
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
        cache_key = self._generate_cache_key(query, params)
        self.cache.set(cache_key, results)
        logger.debug(f"Cached retrieval results for: {query[:50]}")
    
    async def get_or_retrieve(
        self, 
        query: str, 
        params: Dict[str, Any],
        retrieve_fn
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
        # Try cache first
        cached = await self.get_cached_results(query, params)
        if cached is not None:
            return cached
        
        # Cache miss - retrieve
        results = await retrieve_fn(query, **params)
        
        # Cache for next time
        await self.cache_results(query, params, results)
        
        return results
    
    def clear_cache(self):
        """Clear all cached retrieval results"""
        # Clear only retrieval keys
        with self.cache.lock:
            retrieval_keys = [k for k in self.cache.cache.keys() if k.startswith("retrieval:")]
            for key in retrieval_keys:
                del self.cache.cache[key]
        
        logger.info(f"Cleared {len(retrieval_keys)} retrieval cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval cache statistics"""
        stats = self.cache.get_stats()
        
        # Count retrieval-specific entries
        with self.cache.lock:
            retrieval_count = sum(1 for k in self.cache.cache.keys() if k.startswith("retrieval:"))
        
        stats["retrieval_entries"] = retrieval_count
        return stats


# Global cache instances
_session_cache = SessionCache(max_size=1000, default_ttl=300)
_retrieval_cache = RetrievalCache(_session_cache)


def get_session_cache() -> SessionCache:
    """Get global session cache instance"""
    return _session_cache


def get_retrieval_cache() -> RetrievalCache:
    """Get global retrieval cache instance"""
    return _retrieval_cache
