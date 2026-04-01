"""
Rate Limiting Middleware
"""
import logging
import time
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from redis import Redis
import hashlib

logger = logging.getLogger(__name__)

class RateLimiter:
    """Redis-based rate limiter with tiered limits"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        try:
            self.redis_client = Redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Rate limiter initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {str(e)}")
            self.redis_client = None
            self.memory_store = {}
    
    # Tiered rate limits
    RATE_LIMITS = {
        "student": {"requests": 100, "window": 3600},  # 100/hour
        "teacher": {"requests": 500, "window": 3600},  # 500/hour
        "admin": {"requests": 10000, "window": 3600},  # 10000/hour
        "anonymous": {"requests": 20, "window": 3600},  # 20/hour
    }
    
    # Token budgets (daily)
    TOKEN_BUDGETS = {
        "student": 10000,
        "teacher": 50000,
        "admin": 1000000,
        "anonymous": 1000,
    }
    
    async def check_rate_limit(
        self, 
        request: Request,
        user_id: Optional[str] = None,
        user_role: str = "anonymous"
    ) -> Dict[str, any]:
        """
        Check if request is within rate limits
        """
        # Get identifier (user_id or IP)
        identifier = user_id or self._get_client_ip(request)
        
        # Get rate limit for role
        limit_config = self.RATE_LIMITS.get(user_role, self.RATE_LIMITS["anonymous"])
        
        # Check request rate limit
        request_check = await self._check_request_limit(
            identifier, 
            user_role,
            limit_config
        )
        
        if not request_check["allowed"]:
            return request_check
        
        # Check token budget (if user_id provided)
        if user_id:
            token_check = await self._check_token_budget(user_id, user_role)
            if not token_check["allowed"]:
                return token_check
        
        return {
            "allowed": True,
            "remaining": request_check["remaining"],
            "reset_at": request_check["reset_at"]
        }
    
    async def _check_request_limit(
        self, 
        identifier: str, 
        role: str,
        limit_config: Dict
    ) -> Dict:
        """Check request rate limit"""
        key = f"rate_limit:{role}:{identifier}"
        window = limit_config["window"]
        max_requests = limit_config["requests"]
        
        current_time = int(time.time())
        window_start = current_time - window
        
        if self.redis_client:
            # Redis implementation
            try:
                # Remove old entries
                self.redis_client.zremrangebyscore(key, 0, window_start)
                
                # Count requests in current window
                request_count = self.redis_client.zcard(key)
                
                if request_count >= max_requests:
                    # Rate limit exceeded
                    oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                    reset_at = int(oldest[0][1]) + window if oldest else current_time + window
                    
                    return {
                        "allowed": False,
                        "reason": "rate_limit_exceeded",
                        "limit": max_requests,
                        "window": window,
                        "reset_at": reset_at,
                        "remaining": 0
                    }
                
                # Add current request
                self.redis_client.zadd(key, {str(current_time): current_time})
                self.redis_client.expire(key, window)
                
                return {
                    "allowed": True,
                    "remaining": max_requests - request_count - 1,
                    "reset_at": current_time + window
                }
                
            except Exception as e:
                logger.error(f"Redis error in rate limiting: {str(e)}")
                # Fail open (allow request)
                return {"allowed": True, "remaining": max_requests}
        else:
            # In-memory fallback
            if key not in self.memory_store:
                self.memory_store[key] = []
            
            # Remove old entries
            self.memory_store[key] = [
                ts for ts in self.memory_store[key] 
                if ts > window_start
            ]
            
            if len(self.memory_store[key]) >= max_requests:
                return {
                    "allowed": False,
                    "reason": "rate_limit_exceeded",
                    "remaining": 0
                }
            
            self.memory_store[key].append(current_time)
            return {
                "allowed": True,
                "remaining": max_requests - len(self.memory_store[key])
            }
    
    async def _check_token_budget(
        self, 
        user_id: str, 
        role: str
    ) -> Dict:
        """Check daily token budget"""
        key = f"token_budget:{user_id}"
        daily_budget = self.TOKEN_BUDGETS.get(role, self.TOKEN_BUDGETS["anonymous"])
        
        if self.redis_client:
            try:
                # Get current usage
                usage = self.redis_client.get(key)
                current_usage = int(usage) if usage else 0
                
                if current_usage >= daily_budget:
                    return {
                        "allowed": False,
                        "reason": "token_budget_exceeded",
                        "budget": daily_budget,
                        "used": current_usage,
                        "remaining": 0
                    }
                
                return {
                    "allowed": True,
                    "budget": daily_budget,
                    "used": current_usage,
                    "remaining": daily_budget - current_usage
                }
                
            except Exception as e:
                logger.error(f"Redis error checking token budget: {str(e)}")
                return {"allowed": True}
        else:
            # Fail open without Redis
            return {"allowed": True}
    
    async def track_token_usage(
        self, 
        user_id: str, 
        tokens_used: int
    ):
        """Track token usage for budget enforcement"""
        key = f"token_budget:{user_id}"
        
        if self.redis_client:
            try:
                # Increment usage
                self.redis_client.incrby(key, tokens_used)
                
                # Set expiry to end of day (86400 seconds)
                current_time = int(time.time())
                seconds_until_midnight = 86400 - (current_time % 86400)
                self.redis_client.expire(key, seconds_until_midnight)
                
            except Exception as e:
                logger.error(f"Error tracking token usage: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def get_rate_limit_status(
        self, 
        user_id: str, 
        role: str
    ) -> Dict:
        """Get current rate limit status for user"""
        request_key = f"rate_limit:{role}:{user_id}"
        token_key = f"token_budget:{user_id}"
        
        limit_config = self.RATE_LIMITS.get(role, self.RATE_LIMITS["anonymous"])
        token_budget = self.TOKEN_BUDGETS.get(role, self.TOKEN_BUDGETS["anonymous"])
        
        if self.redis_client:
            try:
                # Request count
                request_count = self.redis_client.zcard(request_key)
                
                # Token usage
                token_usage = self.redis_client.get(token_key)
                token_usage = int(token_usage) if token_usage else 0
                
                return {
                    "requests": {
                        "used": request_count,
                        "limit": limit_config["requests"],
                        "remaining": limit_config["requests"] - request_count,
                        "window": limit_config["window"]
                    },
                    "tokens": {
                        "used": token_usage,
                        "budget": token_budget,
                        "remaining": token_budget - token_usage
                    }
                }
            except Exception as e:
                logger.error(f"Error getting rate limit status: {str(e)}")
        
        return {
            "requests": {"limit": limit_config["requests"]},
            "tokens": {"budget": token_budget}
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

class RateLimiterMiddleware:
    """
    FastAPI Middleware for Rate Limiting
    
    Integrates RateLimiter with FastAPI request/response cycle.
    Checks rate limits before processing requests and adds rate limit headers to responses.
    """
    
    def __init__(self, app):
        self.app = app
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation"""
        if scope["type"] != "http":
            # Only process HTTP requests
            await self.app(scope, receive, send)
            return
        
        # Create request object for rate limit check
        from fastapi import Request
        request = Request(scope, receive)
        
        # Extract user information from headers
        user_id = request.headers.get("X-User-ID")
        user_role = request.headers.get("X-User-Role", "anonymous")
        
        # Check rate limit
        try:
            result = await self.rate_limiter.check_rate_limit(
                request, 
                user_id, 
                user_role
            )
            
            if not result["allowed"]:
                # Rate limit exceeded - return 429 response
                from fastapi.responses import JSONResponse
                
                response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Rate limit exceeded: {result.get('reason', 'Too many requests')}",
                        "limit": result.get("limit"),
                        "window": result.get("window"),
                        "reset_at": result.get("reset_at"),
                        "remaining": 0
                    }
                )
                
                await response(scope, receive, send)
                return
            
            # Rate limit OK - process request and add headers
            async def send_with_headers(message):
                if message["type"] == "http.response.start":
                    # Add rate limit headers to response
                    headers = list(message.get("headers", []))
                    headers.append((
                        b"x-ratelimit-remaining",
                        str(result.get("remaining", 0)).encode()
                    ))
                    headers.append((
                        b"x-ratelimit-limit",
                        str(result.get("limit", 0)).encode()
                    ))
                    headers.append((
                        b"x-ratelimit-reset",
                        str(result.get("reset_at", 0)).encode()
                    ))
                    message["headers"] = headers
                
                await send(message)
            
            await self.app(scope, receive, send_with_headers)
            
        except Exception as e:
            logger.error(f"Rate limiter middleware error: {str(e)}")
            # Fail open - allow request on error
            await self.app(scope, receive, send)
