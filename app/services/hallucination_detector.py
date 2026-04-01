"""
Hallucination Detection Service
Multi-method approach to detect AI hallucinations
"""
import logging
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class HallucinationDetector:
    """
    Multi-method hallucination detection
    Uses LLM self-checking, embedding similarity, and keyword matching
    """
    
    def __init__(self, llm_service: LLMService, embedding_model):
        self.llm = llm_service
        self.embedding_model = embedding_model
    
    async def detect_hallucination(
        self, 
        response: str, 
        source_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect hallucinations using multiple methods
        
        Args:
            response: AI-generated response
            source_docs: Source documents used for generation
        
        Returns:
            Dict with risk_level, confidence, and method details
        """
        try:
            # Method 1: LLM-based self-checking
            llm_check = await self._llm_based_check(response, source_docs)
            
            # Method 2: Embedding similarity
            similarity_check = await self._embedding_similarity_check(response, source_docs)
            
            # Method 3: Keyword matching
            keyword_check = self._keyword_matching_check(response, source_docs)
            
            # Aggregate risk scores
            risk_scores = [
                llm_check['risk'],
                similarity_check['risk'],
                keyword_check['risk']
            ]
            avg_risk = np.mean(risk_scores)
            
            # Determine risk level
            if avg_risk < 0.3:
                risk_level = "low"
            elif avg_risk < 0.7:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            result = {
                "risk_level": risk_level,
                "risk_score": float(avg_risk),
                "confidence": float(1 - avg_risk),
                "methods": {
                    "llm_check": llm_check,
                    "similarity_check": similarity_check,
                    "keyword_check": keyword_check
                },
                "recommendation": self._get_recommendation(risk_level)
            }
            
            logger.info(f"Hallucination detection: {risk_level} (score: {avg_risk:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in hallucination detection: {str(e)}")
            return {
                "risk_level": "unknown",
                "risk_score": 0.5,
                "confidence": 0.5,
                "error": str(e)
            }
    
    async def _llm_based_check(
        self, 
        response: str, 
        source_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ask LLM to verify its own response against sources
        """
        try:
            source_texts = [doc['text'][:200] for doc in source_docs[:3]]
            
            prompt = f"""
Rate how well this answer follows from the source documents on a scale of 1-10.
Only respond with a single number.

Answer: {response[:500]}

Sources:
{chr(10).join([f"- {text}" for text in source_texts])}

Rating (1-10):"""
            
            rating_str = await self.llm.generate_response(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            # Extract number
            try:
                rating = float(''.join(filter(str.isdigit, rating_str)))
                rating = min(max(rating, 1), 10)  # Clamp to 1-10
            except:
                rating = 5  # Default to medium confidence
            
            confidence = rating / 10
            risk = 1 - confidence
            
            return {
                "method": "llm_self_check",
                "confidence": confidence,
                "risk": risk,
                "rating": rating
            }
            
        except Exception as e:
            logger.error(f"LLM check error: {str(e)}")
            return {"method": "llm_self_check", "confidence": 0.5, "risk": 0.5}
    
    async def _embedding_similarity_check(
        self, 
        response: str, 
        source_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check embedding similarity between response and sources
        """
        try:
            # Generate response embedding
            response_embedding = self.embedding_model.encode([response])[0]
            
            # Generate source embeddings
            source_texts = [doc['text'] for doc in source_docs]
            source_embeddings = self.embedding_model.encode(source_texts)
            
            # Calculate max similarity
            similarities = cosine_similarity(
                [response_embedding], 
                source_embeddings
            )[0]
            
            max_similarity = float(np.max(similarities))
            avg_similarity = float(np.mean(similarities))
            
            # Low similarity = likely hallucination
            risk = 1 - max_similarity
            
            return {
                "method": "embedding_similarity",
                "max_similarity": max_similarity,
                "avg_similarity": avg_similarity,
                "confidence": max_similarity,
                "risk": risk
            }
            
        except Exception as e:
            logger.error(f"Embedding similarity error: {str(e)}")
            return {"method": "embedding_similarity", "confidence": 0.5, "risk": 0.5}
    
    def _keyword_matching_check(
        self, 
        response: str, 
        source_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if response keywords appear in source documents
        """
        try:
            # Extract keywords from response (simple word-based)
            response_words = set(response.lower().split())
            
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                         'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were'}
            response_keywords = response_words - stop_words
            
            if not response_keywords:
                return {"method": "keyword_matching", "confidence": 0.5, "risk": 0.5}
            
            # Combine all source text
            source_text = " ".join([doc['text'].lower() for doc in source_docs])
            
            # Count matched keywords
            matched = sum(1 for kw in response_keywords if kw in source_text)
            match_ratio = matched / len(response_keywords)
            
            # Low match ratio = likely hallucination
            risk = 1 - match_ratio
            
            return {
                "method": "keyword_matching",
                "match_ratio": match_ratio,
                "matched_keywords": matched,
                "total_keywords": len(response_keywords),
                "confidence": match_ratio,
                "risk": risk
            }
            
        except Exception as e:
            logger.error(f"Keyword matching error: {str(e)}")
            return {"method": "keyword_matching", "confidence": 0.5, "risk": 0.5}
    
    def _get_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            "low": "Response appears well-grounded in source documents.",
            "medium": "⚠️ The system is somewhat uncertain about this answer. Please verify with additional sources.",
            "high": "⚠️ HIGH RISK: This response may contain inaccurate information. Please consult a teacher or verify independently."
        }
        return recommendations.get(risk_level, "Unable to assess response reliability.")
