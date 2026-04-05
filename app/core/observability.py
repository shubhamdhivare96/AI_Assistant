"""
Observability core module for AI Assistant
Provides tracing and monitoring utilities
"""
import os
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TraceSpan:
    """A simple trace span for observability"""
    def __init__(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.metadata = metadata or {}
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"[TRACE] START: {self.name} | Metadata: {self.metadata}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        status = "SUCCESS" if exc_type is None else f"FAILED ({exc_type.__name__})"
        logger.info(f"[TRACE] END: {self.name} | Status: {status} | Duration: {self.duration:.3f}s")
        
        # If LangChain/LangSmith was available, we would log to it here
        # For now, we use structured logging as the base for observability

class ObservabilityManager:
    """Manager for observability and tracing"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ObservabilityManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
        self.project_name = os.getenv("LANGSMITH_PROJECT", "ai-assistant-v1")
        self._initialized = True
        
        if self.enabled:
            logger.info(f"Observability enabled (Project: {self.project_name})")
        else:
            logger.info("Observability initialized in logging-only mode")

    def trace_span(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> TraceSpan:
        """Create a new trace span"""
        return TraceSpan(name, metadata)

# Singleton instance
observability = ObservabilityManager()
