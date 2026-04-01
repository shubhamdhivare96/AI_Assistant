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
    Combines BM25 (keyword/sparse) and Vector (semantic/dense) search
    """
    
    def __init__(self):
        super().__init__()
        self.bm25_index = None
        self.documents = []
        self.document_ids = []
        self.alpha = 0.5  # 50/50 weighting between dense and sparse
        self.settings = get_settings()
        
    def build_bm25_index(self, documents: List[Dict[str, Any]]):
        """Build BM25 index from documents"""
        try:
            self.documents = [doc['text'] for doc in documents]
            self.document_ids = [doc.get('id', str(uuid.uuid4())) for doc in documents]
            
            # Tokenize documents for BM25
            tokenized_docs = [nltk.word_tokenize(doc.lower()) for doc in self.documents]
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(tokenized_docs)
            
            logger.info(f"Built BM25 index with {len(self.documents)} documents")
            
        except Exception as e:
            logger.error(f"Error building BM25 index: {str(e)}")
            raise
    
    async def hybrid_search(self, query: str, top_k: int = 100, 
                           alpha: Optional[float] = None) -> List[Dict[str, Any]]:
        """Hybrid search combining BM25 and vector search"""
        try:
            # Debug logging to catch the dict error
            logger.info(f"hybrid_search called with query type: {type(query)}")
            logger.info(f"hybrid_search called with query value: {query}")
            
            if not isinstance(query, str):
                logger.error(f"Expected string but got {type(query)}: {query}")
                # Convert to string as fallback
                if isinstance(query, dict):
                    query = query.get('reformulated', str(query))
                else:
                    query = str(query)
            
            if alpha is None:
                alpha = self.alpha
            
            # If BM25 index was never built for this session (documents list is empty),
            # just return the pure vector search results directly.
            # Otherwise we'd discard the vector results trying to map them.
            if self.bm25_index is None or not self.documents:
                logger.info("BM25 index not initialized; falling back to pure vector search")
                return await super().search_similar(query, top_k=top_k)
            
            # BM25 sparse search
            bm25_scores = await self._bm25_search(query)
            
            # Vector dense search
            vector_scores = await self._vector_search(query, top_k=top_k)
            
            # Combine scores
            hybrid_scores = self._combine_scores(bm25_scores, vector_scores, alpha)
            
            # Get top-k results
            top_indices = np.argsort(hybrid_scores)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if idx < len(self.documents):
                    results.append({
                        'id': self.document_ids[idx],
                        'text': self.documents[idx],
                        'score': float(hybrid_scores[idx]),
                        'metadata': {'retrieval_method': 'hybrid'}
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return await super().search_similar(query, top_k=top_k)
    
    async def _bm25_search(self, query: str) -> np.ndarray:
        """Perform BM25 sparse search"""
        if self.bm25_index is None:
            return np.zeros(len(self.documents))
        
        # Debug logging to catch the dict error
        logger.info(f"_bm25_search called with query type: {type(query)}")
        logger.info(f"_bm25_search called with query value: {query}")
        
        if not isinstance(query, str):
            logger.error(f"Expected string but got {type(query)}: {query}")
            query = str(query)
        
        tokenized_query = nltk.word_tokenize(query.lower())
        return self.bm25_index.get_scores(tokenized_query)
    
    async def _vector_search(self, query: str, top_k: int = 100) -> Dict[int, float]:
        """Perform vector dense search"""
        try:
            vector_results = await super().search_similar(query, top_k=top_k)
            vector_scores = {}
            for result in vector_results:
                try:
                    idx = self.documents.index(result['text'])
                    vector_scores[idx] = result['score']
                except ValueError:
                    continue
            return vector_scores
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return {}
    
    def _combine_scores(self, bm25_scores: np.ndarray, 
                       vector_scores: Dict[int, float], alpha: float) -> np.ndarray:
        """Combine BM25 and vector scores with alpha weighting"""
        # Handle empty arrays
        if len(bm25_scores) == 0:
            return np.array([])
        
        # Normalize BM25 scores
        if bm25_scores.max() > 0:
            bm25_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min())
        else:
            bm25_norm = bm25_scores
        
        # Create vector scores array
        vector_array = np.zeros(len(self.documents))
        for idx, score in vector_scores.items():
            if idx < len(vector_array):
                vector_array[idx] = score
        
        # Normalize vector scores
        if len(vector_array) > 0 and vector_array.max() > 0:
            vector_norm = (vector_array - vector_array.min()) / (vector_array.max() - vector_array.min())
        else:
            vector_norm = vector_array
        
        # Combine: alpha * dense + (1-alpha) * sparse
        return alpha * vector_norm + (1 - alpha) * bm25_norm
