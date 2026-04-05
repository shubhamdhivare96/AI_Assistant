"""
Hybrid RAG Service - Combines BM25 (sparse) and Vector (dense) search
"""
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import nltk
from datetime import datetime
import uuid

from app.services.rag_service import RAGService
from app.config import get_settings

logger = logging.getLogger(__name__)

# Download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class HybridRAGService(RAGService):
    """
    Hybrid Retrieval-Augmented Generation Service
    Uses Qdrant's native Hybrid (Dense + Sparse) search
    """
    
    def __init__(self):
        super().__init__()
        self.alpha = 0.5  # Default weighting
        
    def build_bm25_index(self, documents: List[Dict[str, Any]]):
        """No longer needed - Sparse vectors are managed by Qdrant"""
        logger.info("Local BM25 index build skipped - using Qdrant Sparse Vectors")
        pass
    
    async def hybrid_search(self, query: str, top_k: int = 10, 
                           alpha: Optional[float] = None) -> List[Dict[str, Any]]:
        """Hybrid search using Qdrant's native fusion"""
        if alpha is None:
            alpha = self.alpha
            
        # Use the newly implemented hybrid search in the base class
        return await self.search_similar(query, top_k=top_k, alpha=alpha)
