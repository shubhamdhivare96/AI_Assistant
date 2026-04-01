"""
Query Reformulation Service
Rewrites ambiguous queries for better retrieval
"""
import logging
from typing import List, Dict, Any
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class QueryReformulator:
    """
    Query Reformulation Service
    Rewrites vague/ambiguous queries into explicit, searchable versions
    """
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
    
    async def reformulate_query(
        self, 
        query: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Reformulate query for better retrieval
        
        Args:
            query: Original user query
            conversation_history: Recent conversation messages
        
        Returns:
            Dict with original and reformulated query
        """
        try:
            # Check if reformulation is needed
            if not self._needs_reformulation(query):
                return {
                    "original": query,
                    "reformulated": query,
                    "was_reformulated": False,
                    "reason": "Query is already explicit"
                }
            
            # Build reformulation prompt
            system_prompt = """You are a query reformulation assistant for an educational platform.
Your task is to rewrite user queries to be:
1. Explicit (resolve pronouns like 'it', 'that', 'this')
2. Specific (add relevant context and keywords)
3. Searchable (optimize for document retrieval)
4. Clear (remove ambiguity)

Use conversation history to resolve references.
Output ONLY the reformulated query, nothing else."""
            
            # Include recent conversation context
            context_messages = []
            if conversation_history:
                context_messages = conversation_history[-3:]  # Last 3 messages
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation context
            # Handle both Pydantic Message objects and plain dicts
            for msg in context_messages:
                if hasattr(msg, 'role'):
                    # Pydantic Message object
                    role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                    content = msg.content
                else:
                    # Plain dict
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                messages.append({"role": role, "content": content})
            
            # Add reformulation request
            messages.append({
                "role": "user",
                "content": f"Reformulate this query: {query}"
            })
            
            # Generate reformulated query
            reformulated = await self.llm.generate_response(
                messages,
                temperature=0.1,
                max_tokens=100
            )
            
            reformulated = reformulated.strip()
            
            logger.info(f"Reformulated: '{query}' -> '{reformulated}'")
            
            return {
                "original": query,
                "reformulated": reformulated,
                "was_reformulated": True,
                "reason": "Query was ambiguous or vague"
            }
            
        except Exception as e:
            logger.error(f"Error reformulating query: {str(e)}")
            return {
                "original": query,
                "reformulated": query,
                "was_reformulated": False,
                "error": str(e)
            }
    
    def _needs_reformulation(self, query: str) -> bool:
        """
        Check if query needs reformulation
        
        Returns:
            True if query is ambiguous/vague
        """
        query_lower = query.lower()
        
        # Check for pronouns
        pronouns = ['it', 'that', 'this', 'these', 'those', 'they', 'them']
        has_pronouns = any(f" {p} " in f" {query_lower} " or 
                          query_lower.startswith(f"{p} ") 
                          for p in pronouns)
        
        # Check for vague phrases
        vague_phrases = [
            'tell me more', 'what about', 'how about',
            'explain', 'what is', 'can you'
        ]
        has_vague = any(phrase in query_lower for phrase in vague_phrases)
        
        # Check if query is very short
        is_short = len(query.split()) < 4
        
        # Check for question words without specifics
        question_words = ['what', 'how', 'why', 'when', 'where']
        has_question = any(word in query_lower for word in question_words)
        
        # Needs reformulation if:
        # - Has pronouns OR
        # - Is vague and short OR
        # - Has question word but is very short
        needs_reform = (
            has_pronouns or
            (has_vague and is_short) or
            (has_question and len(query.split()) < 3)
        )
        
        return needs_reform
