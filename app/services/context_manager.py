"""
Context Management & Token Optimization Service
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ContextManager:
    """Manages context and optimizes token usage"""
    
    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens
        # Use approximate tokenizer (Gemini doesn't have public tokenizer)
        # Rough estimate: 1 token ≈ 4 characters
        self.chars_per_token = 4
        
    def count_tokens(self, text: str) -> int:
        """Count tokens (approximate for Gemini)"""
        return len(text) // self.chars_per_token
    
    async def optimize_context(
        self, 
        retrieved_docs: List[Dict], 
        query: str
    ) -> str:
        """
        Optimize context to fit within token budget
        """
        # Sort by relevance score
        sorted_docs = sorted(
            retrieved_docs, 
            key=lambda x: x.get('score', 0), 
            reverse=True
        )
        
        context_parts = []
        total_tokens = 0
        
        for i, doc in enumerate(sorted_docs):
            doc_text = doc['text']
            doc_tokens = self.count_tokens(doc_text)
            
            # Check if adding this doc exceeds budget
            if total_tokens + doc_tokens > self.max_context_tokens:
                # Truncate or summarize
                remaining_tokens = self.max_context_tokens - total_tokens
                if remaining_tokens > 100:
                    # Truncate to fit
                    truncated = self._truncate_to_tokens(doc_text, remaining_tokens)
                    context_parts.append(f"[Document {i+1} (truncated)]: {truncated}")
                break
            
            context_parts.append(f"[Document {i+1}]: {doc_text}")
            total_tokens += doc_tokens
        
        logger.info(f"Optimized context: {total_tokens} tokens from {len(sorted_docs)} documents")
        return "\n\n".join(context_parts)
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit token budget"""
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens) + "..."
    
    async def create_optimized_prompt(
        self, 
        query: str, 
        context: str, 
        conversation_history: List[Dict]
    ) -> List[Dict]:
        """
        Create optimized prompt with token management
        """
        # System prompt
        system_prompt = "You are an educational AI assistant. Provide accurate, clear answers based on the context provided."
        system_tokens = self.count_tokens(system_prompt)
        
        # Context tokens
        context_tokens = self.count_tokens(context)
        
        # History tokens (last 3 messages)
        history_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
            for msg in conversation_history[-3:]
        ])
        history_tokens = self.count_tokens(history_text)
        
        # Query tokens
        query_tokens = self.count_tokens(query)
        
        total_tokens = system_tokens + context_tokens + history_tokens + query_tokens
        
        logger.info(f"Total context tokens: {total_tokens} / {self.max_context_tokens}")
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add history if space allows
        if history_tokens < 500:
            for msg in conversation_history[-3:]:
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
        
        # Add context and query
        messages.append({
            "role": "user", 
            "content": f"Context:\n{context}\n\nQuestion: {query}"
        })
        
        return messages
    
    def get_token_stats(self, text: str) -> Dict[str, Any]:
        """Get token statistics for text"""
        tokens = self.tokenizer.encode(text)
        return {
            "token_count": len(tokens),
            "character_count": len(text),
            "tokens_per_char": len(tokens) / len(text) if text else 0,
            "estimated_cost": self._estimate_cost(len(tokens))
        }
    
    def _estimate_cost(self, token_count: int) -> float:
        """Estimate cost based on token count (GPT-4 pricing)"""
        # GPT-4 pricing: ~$0.03 per 1K tokens (input)
        return (token_count / 1000) * 0.03
