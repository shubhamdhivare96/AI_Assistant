"""
Application settings
"""
import os
from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "AI Assistant API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API Keys (set in .env file)
    GOOGLE_API_KEY: Optional[str] = None  # Primary LLM (Gemini)
    GROQ_API_KEY: Optional[str] = None  # Fallback LLM
    AWS_ACCESS_KEY_ID: Optional[str] = None  # For Nova embeddings
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Vector Database
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    
    # File uploads
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "txt", "doc", "docx", "png", "jpg", "jpeg"]
    UPLOAD_FOLDER: str = "./uploads"
    
    # RAG Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Hierarchical Chunking Configuration (for Python documentation)
    ENABLE_HIERARCHICAL_CHUNKING: bool = True
    PARENT_CHUNK_SIZE: int = 2000  # Large context for LLM
    CHILD_CHUNK_SIZE: int = 500    # Precise retrieval
    PARENT_OVERLAP: int = 200
    CHILD_OVERLAP: int = 50
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = "amazon.nova-2-multimodal-embeddings-v1:0"  # Primary (AWS Nova)
    EMBEDDING_DIMENSIONS: int = 1024  # Nova 2 dimensions
    EMBEDDING_MAX_TOKENS: int = 8172  # Nova 2 max tokens
    FALLBACK_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # Fallback
    FALLBACK_EMBEDDING_DIMENSIONS: int = 384
    
    # LLM Configuration
    LLM_PROVIDER: str = "google"  # Primary: Google Gemini
    LLM_MODEL: str = "gemini-2.0-flash"  # Confirmed available on v1beta API
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    FALLBACK_LLM_PROVIDER: str = "groq"  # Fallback: Groq
    FALLBACK_LLM_MODEL: str = "llama-3.1-70b-versatile"
    NOVA_LLM_MODEL: str = "amazon.nova-pro-v1:0"  # Fallback #2: AWS Bedrock Nova Pro
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # 1 hour
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "ai_assistant.log"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Advanced RAG Configuration
    HYBRID_SEARCH_ALPHA: float = 0.5  # 0.5 = equal weight BM25 and vector
    RERANKING_ENABLED: bool = True
    RERANKING_TOP_K: int = 100  # Rerank top 100 to get best 10
    HALLUCINATION_DETECTION_ENABLED: bool = True
    PII_MASKING_ENABLED: bool = True
    PII_MASKING_STRATEGY: str = "hash"  # "replace", "redact", or "hash"
    QUERY_REFORMULATION_ENABLED: bool = True
    ADAPTIVE_ROUTING_ENABLED: bool = True
    MULTIHOP_RETRIEVAL_ENABLED: bool = True
    MULTIHOP_MAX_HOPS: int = 3
    BIAS_DETECTION_ENABLED: bool = True
    SECURE_RETRIEVAL_ENABLED: bool = True
    RETRIEVAL_CACHE_ENABLED: bool = True
    RETRIEVAL_CACHE_TTL: int = 300  # 5 minutes
    CONTEXT_MAX_TOKENS: int = 4000
    PERFORMANCE_MONITORING_ENABLED: bool = True
    
    # Security Configuration
    PROMPT_INJECTION_DETECTION_ENABLED: bool = True
    DOMAIN_CLASSIFICATION_ENABLED: bool = True
    DOMAIN_DESCRIPTION: str = "Educational content from NCERT curriculum (Science, Math, Social Studies)"
    INJECTION_BLOCK_THRESHOLD: float = 0.7  # Block if risk > 0.7
    DOMAIN_CONFIDENCE_THRESHOLD: float = 0.7  # Reject if out-of-domain confidence > 0.7
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    
    # Email (for notifications)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Feature flags
    ENABLE_CHAT_HISTORY: bool = True
    ENABLE_FILE_UPLOAD: bool = True
    ENABLE_VOICE_INPUT: bool = False
    ENABLE_IMAGE_PROCESSING: bool = True
    
    # Resilience Configuration
    CIRCUIT_BREAKER_ENABLED: bool = True
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_FACTOR: int = 2
    FALLBACK_ENABLED: bool = True
    CACHE_FALLBACK_TTL: int = 3600
    
    # Data Retention (GDPR)
    DATA_RETENTION_DAYS: int = 90
    SOFT_DELETE_RETENTION_DAYS: int = 7
    
    # Token Budget Configuration
    TOKEN_BUDGET_ENABLED: bool = True
    TOKEN_BUDGET_STUDENT: int = 50000      # tokens per day
    TOKEN_BUDGET_TEACHER: int = 200000
    TOKEN_BUDGET_ADMIN: int = 1000000
    TOKEN_BUDGET_PREMIUM: int = 500000
    TOKEN_BUDGET_FREE: int = 10000
    TOKEN_BUDGET_SOFT_THRESHOLD: float = 0.8  # Warn at 80%
    
    # Anomaly Detection Configuration
    ANOMALY_DETECTION_ENABLED: bool = True
    ANOMALY_SPIKE_THRESHOLD_SIGMA: float = 3.0
    ANOMALY_RAPID_FIRE_THRESHOLD: int = 10  # requests per minute
    ANOMALY_COST_SPIKE_MULTIPLIER: float = 5.0
    ANOMALY_TOKEN_SPIKE_MULTIPLIER: float = 5.0
    ANOMALY_ALERT_EMAIL: Optional[str] = None  # Email for critical alerts
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Create settings instance
settings = get_settings()
