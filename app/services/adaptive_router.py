"""
Adaptive Routing Service
Routes queries to appropriate retrieval strategy based on complexity
"""
import logging
from typing import Dict, Any, List
import re

logger = logging.getLogger(__name__)

class AdaptiveRouter:
    """
    Adaptive Query Routing
    Analyzes query complexity and routes to appropriate strategy
    """
    
    def __init__(self):
        self.complexity_threshold = 3  # Threshold for simple vs complex
        
        # Keywords indicating complexity
        self.complex_keywords = [
            'compare', 'contrast', 'difference', 'versus', 'vs',
            'analyze', 'evaluate', 'explain how', 'why does',
            'relationship', 'connection', 'impact', 'effect',
            'multiple', 'several', 'various', 'different'
        ]
        
        self.question_words = [
            'what', 'why', 'how', 'when', 'where', 'who',
            'which', 'whose', 'whom'
        ]
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine complexity
        
        Returns:
            Dict with complexity analysis
        """
        # Debug logging to catch the dict error
        logger.info(f"analyze_query_complexity called with query type: {type(query)}")
        logger.info(f"analyze_query_complexity called with query value: {query}")
        
        if not isinstance(query, str):
            logger.error(f"Expected string but got {type(query)}: {query}")
            # Convert to string as fallback
            if isinstance(query, dict):
                query = query.get('reformulated', str(query))
            else:
                query = str(query)
        
        query_lower = query.lower()
        
        # Count question words
        question_count = sum(
            1 for word in self.question_words 
            if word in query_lower
        )
        
        # Check for complex keywords
        has_complex_keywords = any(
            keyword in query_lower 
            for keyword in self.complex_keywords
        )
        
        # Extract entities (simple word count heuristic)
        words = query.split()
        capitalized_words = [w for w in words if w[0].isupper() and len(w) > 1]
        entity_count = len(capitalized_words)
        
        # Check for comparison patterns
        has_comparison = any(
            word in query_lower 
            for word in ['compare', 'contrast', 'versus', 'vs', 'difference']
        )
        
        # Check for multi-part questions
        has_multiple_questions = query.count('?') > 1 or query.count(' and ') > 1
        
        # Calculate complexity score
        complexity_score = (
            question_count +
            entity_count +
            (2 if has_complex_keywords else 0) +
            (2 if has_comparison else 0) +
            (2 if has_multiple_questions else 0)
        )
        
        # Determine complexity level
        if complexity_score < self.complexity_threshold:
            complexity = "simple"
            strategy = "fast_path"
        else:
            complexity = "complex"
            strategy = "full_pipeline"
        
        analysis = {
            "complexity": complexity,
            "complexity_score": complexity_score,
            "strategy": strategy,
            "features": {
                "question_count": question_count,
                "entity_count": entity_count,
                "has_complex_keywords": has_complex_keywords,
                "has_comparison": has_comparison,
                "has_multiple_questions": has_multiple_questions
            }
        }
        
        logger.info(f"Query complexity: {complexity} (score: {complexity_score})")
        return analysis
    
    async def route_query(
        self, 
        query: str,
        rag_service,
        reranker=None,
        multihop_retriever=None
    ) -> Dict[str, Any]:
        """
        Route query to appropriate retrieval strategy
        
        Args:
            query: User query
            rag_service: RAG service instance
            reranker: Optional reranking service
            multihop_retriever: Optional multi-hop retriever
        
        Returns:
            Dict with results and routing info
        """
        # Analyze complexity
        analysis = self.analyze_query_complexity(query)
        
        if analysis["strategy"] == "fast_path":
            # Fast path: Basic retrieval only
            results = await self._fast_retrieval(query, rag_service)
        else:
            # Full pipeline: Hybrid + reranking + multi-hop
            results = await self._full_retrieval(
                query, rag_service, reranker, multihop_retriever
            )
        
        return {
            "results": results,
            "routing": analysis,
            "strategy_used": analysis["strategy"]
        }
    
    async def _fast_retrieval(self, query: str, rag_service) -> List[Dict]:
        """
        Fast retrieval path for simple queries
        - Basic vector search
        - No reranking
        - Top-5 results
        """
        try:
            results = await rag_service.search_similar(query, top_k=5)
            logger.info(f"Fast path: Retrieved {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Fast retrieval error: {str(e)}")
            return []
    
    async def _full_retrieval(
        self, 
        query: str, 
        rag_service,
        reranker=None,
        multihop_retriever=None
    ) -> List[Dict]:
        """
        Full retrieval pipeline for complex queries
        - Hybrid search (top-100)
        - Cross-encoder reranking (top-10)
        - Optional multi-hop
        """
        try:
            # Step 1: Hybrid search for top-100 candidates
            if hasattr(rag_service, 'hybrid_search'):
                candidates = await rag_service.hybrid_search(query, top_k=100)
            else:
                candidates = await rag_service.search_similar(query, top_k=100)
            
            logger.info(f"Full path: Retrieved {len(candidates)} candidates")
            
            # Step 2: Rerank to top-10
            if reranker:
                results = await reranker.rerank(query, candidates, top_k=10)
                logger.info(f"Full path: Reranked to {len(results)} results")
            else:
                results = candidates[:10]
            
            # Step 3: Optional multi-hop for very complex queries
            # (Can be added later)
            
            return results
            
        except Exception as e:
            logger.error(f"Full retrieval error: {str(e)}")
            return []
    
    def set_complexity_threshold(self, threshold: int):
        """Set complexity threshold for routing"""
        self.complexity_threshold = threshold
        logger.info(f"Set complexity threshold to {threshold}")
