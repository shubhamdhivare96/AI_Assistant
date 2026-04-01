"""
Fallback Response Service
NOTE: Redis is optional - system works without it
"""
import logging
from typing import Dict, List, Optional, Any
import json

# Redis is optional
try:
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Redis not available - fallback service will use in-memory only")

logger = logging.getLogger(__name__)

class FallbackService:
    """Provide fallback responses when LLM is unavailable"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = None
        
        # Try to connect to Redis if available
        if REDIS_AVAILABLE:
            try:
                self.redis_client = Redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Fallback service connected to Redis")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory fallback only")
                self.redis_client = None
        else:
            logger.info("Fallback service using in-memory storage (Redis not installed)")
        
        # Rule-based templates for common queries
        self.templates = {
            "greeting": "Hello! I'm an AI assistant for educational content. How can I help you today?",
            "thanks": "You're welcome! Feel free to ask more questions.",
            "unclear": "I'm not sure I understand. Could you rephrase your question?",
            "error": "I'm experiencing technical difficulties. Please try again in a moment.",
            "maintenance": "The system is currently under maintenance. Please try again shortly."
        }
        
        # Common educational responses
        self.common_responses = {
            "what is photosynthesis": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of sugar.",
            "newton's laws": "Newton's three laws of motion describe the relationship between forces and motion: 1) An object at rest stays at rest, 2) F=ma, 3) Every action has an equal and opposite reaction.",
            "pythagorean theorem": "The Pythagorean theorem states that in a right triangle, a² + b² = c², where c is the hypotenuse."
        }
    
    async def get_fallback_response(
        self, 
        query: str,
        conversation_history: List[Dict] = None
    ) -> Dict[str, any]:
        """
        Get fallback response when LLM is unavailable
        """
        # Ensure query is a string
        if not isinstance(query, str):
            logger.warning(f"get_fallback_response received non-string query: {type(query)}")
            if isinstance(query, dict):
                query = query.get('reformulated', str(query))
            else:
                query = str(query)
        
        query_lower = query.lower().strip()
        
        # Try cached response first
        cached = await self._get_cached_response(query)
        if cached:
            logger.info(f"Returning cached fallback for: {query[:50]}")
            return {
                "response": cached,
                "source": "cache",
                "disclaimer": "⚠️ This is a cached response. The AI service is temporarily unavailable."
            }
        
        # Try rule-based templates
        template_response = self._match_template(query_lower)
        if template_response:
            logger.info(f"Returning template fallback for: {query[:50]}")
            return {
                "response": template_response,
                "source": "template",
                "disclaimer": "⚠️ This is a template response. The AI service is temporarily unavailable."
            }
        
        # Try common responses
        common_response = self._match_common_response(query_lower)
        if common_response:
            logger.info(f"Returning common fallback for: {query[:50]}")
            return {
                "response": common_response,
                "source": "common",
                "disclaimer": "⚠️ This is a pre-generated response. The AI service is temporarily unavailable."
            }
        
        # Default fallback
        logger.info(f"Returning default fallback for: {query[:50]}")
        return {
            "response": self._get_default_fallback(),
            "source": "default",
            "disclaimer": "⚠️ The AI service is temporarily unavailable."
        }
    
    async def _get_cached_response(self, query: str) -> Optional[str]:
        """Get cached response from previous successful queries"""
        if not self.redis_client:
            return None
        
        try:
            key = f"response_cache:{self._normalize_query(query)}"
            cached = self.redis_client.get(key)
            return cached
        except Exception as e:
            logger.error(f"Error getting cached response: {str(e)}")
            return None
    
    async def cache_successful_response(
        self, 
        query: str, 
        response: str,
        ttl: int = 86400  # 24 hours
    ):
        """Cache successful response for fallback"""
        if not self.redis_client:
            return
        
        try:
            key = f"response_cache:{self._normalize_query(query)}"
            self.redis_client.setex(key, ttl, response)
            logger.info(f"Cached response for: {query[:50]}")
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for caching"""
        import hashlib
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _match_template(self, query: str) -> Optional[str]:
        """Match query to template"""
        if any(word in query for word in ["hello", "hi", "hey"]):
            return self.templates["greeting"]
        
        if any(word in query for word in ["thank", "thanks"]):
            return self.templates["thanks"]
        
        return None
    
    def _match_common_response(self, query: str) -> Optional[str]:
        """Match query to common responses"""
        for key, response in self.common_responses.items():
            if key in query:
                return response
        return None
    
    def _get_default_fallback(self) -> str:
        """Get default fallback message"""
        return (
            "I apologize, but I'm experiencing technical difficulties at the moment. "
            "Please try again in a few minutes. If the issue persists, contact support.\n\n"
            "In the meantime, you can:\n"
            "- Try rephrasing your question\n"
            "- Check our documentation\n"
            "- Contact your teacher for immediate assistance"
        )
    
    def get_maintenance_message(self) -> str:
        """Get maintenance mode message"""
        return self.templates["maintenance"]
