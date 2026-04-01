"""
Reranking Service using Cross-Encoder
"""
import logging
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
import numpy as np

logger = logging.getLogger(__name__)

class RerankingService:
    """
    Cross-Encoder Reranking Service
    Reranks retrieval candidates for better relevance
    """
    
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize cross-encoder model
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.cross_encoder = None
        self._model_initialized = False
    
    def _ensure_model_initialized(self):
        """Lazy initialization of cross-encoder model"""
        if not self._model_initialized:
            try:
                self.cross_encoder = CrossEncoder(self.model_name)
                logger.info(f"Loaded cross-encoder model: {self.model_name}")
                self._model_initialized = True
            except Exception as e:
                logger.error(f"Failed to load cross-encoder: {str(e)}")
                raise
    
    async def rerank(
        self, 
        query: str, 
        candidates: List[Dict[str, Any]], 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: Search query
            candidates: List of candidate documents from retrieval
            top_k: Number of top results to return
        
        Returns:
            Reranked list of documents with updated scores
        """
        self._ensure_model_initialized()  # Lazy loading
        try:
            if not candidates:
                return []
            
            # Create query-document pairs
            pairs = [[query, doc['text']] for doc in candidates]
            
            # Score all pairs with cross-encoder
            scores = self.cross_encoder.predict(pairs)
            
            # Sort by score (descending)
            ranked_indices = np.argsort(scores)[::-1]
            
            # Return top-k with updated scores
            reranked_results = []
            for idx in ranked_indices[:top_k]:
                doc = candidates[idx].copy()
                doc['rerank_score'] = float(scores[idx])
                doc['original_score'] = doc.get('score', 0.0)
                doc['score'] = float(scores[idx])  # Update main score
                doc['metadata'] = doc.get('metadata', {})
                doc['metadata']['reranked'] = True
                reranked_results.append(doc)
            
            logger.info(f"Reranked {len(candidates)} candidates to top {len(reranked_results)}")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error in reranking: {str(e)}")
            # Fallback: return original candidates
            return candidates[:top_k]
    
    async def rerank_with_scores(
        self, 
        query: str, 
        candidates: List[Dict[str, Any]]
    ) -> List[tuple]:
        """
        Rerank and return (document, score) tuples
        
        Returns:
            List of (document, rerank_score) tuples
        """
        reranked = await self.rerank(query, candidates, top_k=len(candidates))
        return [(doc, doc['rerank_score']) for doc in reranked]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_name": self.cross_encoder.model.name_or_path,
            "model_type": "cross-encoder",
            "max_length": self.cross_encoder.max_length
        }
