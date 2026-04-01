"""
Domain Classification Service
"""
import logging
from typing import Dict, Any, List
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class DomainClassifier:
    """Classify queries and enforce domain boundaries"""
    
    def __init__(
        self, 
        llm_service: LLMService,
        knowledge_base_description: str = "Educational content from NCERT curriculum (Science, Math, Social Studies)"
    ):
        self.llm = llm_service
        self.domain_description = knowledge_base_description
        
        # Define in-domain topics
        self.in_domain_topics = [
            "science", "physics", "chemistry", "biology",
            "mathematics", "algebra", "geometry", "calculus",
            "history", "geography", "civics", "economics",
            "education", "learning", "study", "exam",
            "NCERT", "curriculum", "textbook", "chapter"
        ]
        
        # Define out-of-domain topics
        self.out_of_domain_topics = [
            "bitcoin", "cryptocurrency", "stock market", "trading",
            "politics", "current events", "news", "celebrities",
            "entertainment", "movies", "sports", "games",
            "personal advice", "medical diagnosis", "legal advice",
            "jokes", "stories", "creative writing"
        ]
    
    async def is_in_domain(self, query: str) -> Dict[str, Any]:
        """
        Check if query is within domain boundaries
        """
        query_lower = query.lower()
        
        # Quick keyword-based check first (fast path)
        keyword_result = self._keyword_based_check(query_lower)
        
        if keyword_result['confidence'] > 0.8:
            # High confidence from keywords, skip LLM
            return keyword_result
        
        # Use LLM for ambiguous cases (slow path)
        llm_result = await self._llm_based_check(query)
        
        # Combine results
        final_result = {
            "in_domain": llm_result['in_domain'],
            "confidence": (keyword_result['confidence'] + llm_result['confidence']) / 2,
            "classification": llm_result['classification'],
            "reason": llm_result['reason'],
            "detected_topic": llm_result.get('detected_topic', 'unknown'),
            "method": "hybrid"
        }
        
        logger.info(
            f"Domain check: {final_result['classification']} "
            f"(confidence: {final_result['confidence']:.2f})"
        )
        
        return final_result
    
    def _keyword_based_check(self, query_lower: str) -> Dict[str, Any]:
        """Fast keyword-based domain check"""
        
        # Count in-domain keywords
        in_domain_count = sum(
            1 for topic in self.in_domain_topics 
            if topic in query_lower
        )
        
        # Count out-of-domain keywords
        out_domain_count = sum(
            1 for topic in self.out_of_domain_topics 
            if topic in query_lower
        )
        
        # Determine classification
        if out_domain_count > 0 and in_domain_count == 0:
            return {
                "in_domain": False,
                "confidence": 0.9,
                "classification": "OUT_OF_DOMAIN",
                "reason": "Query contains out-of-domain keywords"
            }
        elif in_domain_count > 0 and out_domain_count == 0:
            return {
                "in_domain": True,
                "confidence": 0.9,
                "classification": "IN_DOMAIN",
                "reason": "Query contains in-domain keywords"
            }
        else:
            return {
                "in_domain": True,  # Default to allowing
                "confidence": 0.5,  # Low confidence, needs LLM check
                "classification": "UNCERTAIN",
                "reason": "Ambiguous query"
            }
    
    async def _llm_based_check(self, query: str) -> Dict[str, Any]:
        """LLM-based domain classification for ambiguous cases"""
        
        prompt = f"""
You are a domain classifier. Determine if the following query is relevant to this knowledge base.

Knowledge Base Domain: {self.domain_description}

User Query: {query}

Analyze:
1. Is this query asking about topics covered in the knowledge base?
2. Is this query trying to get information outside the domain?

Respond in this exact format:
CLASSIFICATION: IN_DOMAIN or OUT_OF_DOMAIN
CONFIDENCE: 0.0 to 1.0
DETECTED_TOPIC: brief topic description
REASON: one sentence explanation

Example:
CLASSIFICATION: IN_DOMAIN
CONFIDENCE: 0.95
DETECTED_TOPIC: photosynthesis (biology)
REASON: Query asks about a biology concept covered in NCERT curriculum
"""
        
        try:
            response = await self.llm.generate_response(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            # Parse response
            classification = "IN_DOMAIN"
            confidence = 0.5
            detected_topic = "unknown"
            reason = "Unable to classify"
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith("CLASSIFICATION:"):
                    classification = line.split(":", 1)[1].strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except:
                        confidence = 0.5
                elif line.startswith("DETECTED_TOPIC:"):
                    detected_topic = line.split(":", 1)[1].strip()
                elif line.startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()
            
            return {
                "in_domain": classification == "IN_DOMAIN",
                "confidence": confidence,
                "classification": classification,
                "detected_topic": detected_topic,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error in LLM-based domain check: {str(e)}")
            # Default to allowing (fail open for better UX)
            return {
                "in_domain": True,
                "confidence": 0.3,
                "classification": "ERROR",
                "detected_topic": "unknown",
                "reason": f"Classification error: {str(e)}"
            }
    
    def get_rejection_message(
        self, 
        query: str, 
        detected_topic: str
    ) -> str:
        """Generate friendly rejection message for out-of-domain queries"""
        
        base_message = (
            f"I apologize, but I can only answer questions about {self.domain_description}.\n\n"
        )
        
        if detected_topic and detected_topic != "unknown":
            base_message += (
                f"Your question appears to be about: {detected_topic}\n\n"
            )
        
        base_message += (
            "Please ask a question related to the educational topics in my knowledge base, "
            "such as science concepts, mathematical problems, or historical events from the curriculum."
        )
        
        return base_message
    
    def get_example_queries(self) -> List[str]:
        """Get example in-domain queries"""
        return [
            "What is photosynthesis?",
            "Explain Newton's laws of motion",
            "How do you solve quadratic equations?",
            "What caused the French Revolution?",
            "Describe the water cycle",
            "What is the Pythagorean theorem?"
        ]
