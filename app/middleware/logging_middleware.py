"""
Logging middleware for request/response logging
"""
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        return response