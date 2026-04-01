"""
Resilience Layer - Retry Logic + Circuit Breaker
"""
import logging
from typing import Any, Callable, Optional
from functools import wraps
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        timeout_duration: int = 60,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == "OPEN":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_duration:
                    logger.info(f"Circuit {self.name} entering HALF_OPEN state")
                    self.state = "HALF_OPEN"
                    return False
            return True
        return False
    
    def record_success(self):
        """Record successful call"""
        if self.state == "HALF_OPEN":
            logger.info(f"Circuit {self.name} closing after successful call")
            self.state = "CLOSED"
            self.failure_count = 0
        elif self.state == "CLOSED":
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                logger.warning(
                    f"Circuit {self.name} OPENING after {self.failure_count} failures"
                )
                self.state = "OPEN"
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.is_open():
                logger.warning(f"Circuit {self.name} is OPEN, rejecting call")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is open"
                )
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except RateLimitError:
                # 429 rate limit: don't count as circuit failure, propagate immediately
                raise
            except Exception as e:
                self.record_failure()
                raise
        
        return wrapper

class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass

class RateLimitError(Exception):
    """
    Raised on HTTP 429 Too Many Requests.
    These are TRANSIENT quota errors and should NOT:
    - Count toward circuit breaker failure threshold
    - Be retried immediately (the API says to wait 30-60s)
    They fall straight through to the next fallback provider.
    """
    pass

# Circuit breakers for different services
llm_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout_duration=60,
    name="llm_service"
)

# Separate breaker for Groq so Gemini failures don't block the Groq fallback
groq_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout_duration=60,
    name="groq_service"
)

# Separate breaker for AWS Nova Pro (fallback #2)
nova_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout_duration=60,
    name="nova_service"
)

qdrant_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout_duration=30,
    name="qdrant_service"
)

redis_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout_duration=30,
    name="redis_service"
)

def retry_with_exponential_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0
):
    """
    Retry decorator with exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError:
                    # Don't retry rate limits - the API quota needs time to reset
                    raise
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator

# Combined decorator for resilient calls
def resilient_call(
    circuit_breaker: CircuitBreaker,
    max_retries: int = 3
):
    """
    Combined retry + circuit breaker decorator
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @retry_with_exponential_backoff(max_attempts=max_retries)
        @circuit_breaker
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Usage example:
# @resilient_call(llm_breaker, max_retries=3)
# async def call_llm(...):
#     return await llm_service.generate_response(...)
