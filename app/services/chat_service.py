"""
Chat service for handling chat operations with Advanced RAG
Uses in-memory storage and integrates with all restored services
"""
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.schemas.chat import ChatRequest, ChatResponse, Message, ChatHistory
from app.config import get_settings
from app.services.llm_service import LLMService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.reranking_service import RerankingService
from app.services.hallucination_detector import HallucinationDetector
from app.services.pii_masker import PIIMasker
from app.services.query_reformulator import QueryReformulator
from app.services.adaptive_router import AdaptiveRouter
from app.services.retrieval_cache import RetrievalCache
from app.services.performance_monitor import performance_monitor, PerformanceMetrics
from app.services.multihop_retrieval import MultiHopRetriever
from app.services.ethical_bias_detector import EthicalBiasDetector
from app.services.context_manager import ContextManager
from app.services.secure_retrieval import SecureRetrievalService
from app.services.prompt_injection_detector import PromptInjectionDetector
from app.services.domain_classifier import DomainClassifier
from app.services.fallback_service import FallbackService

# Restored services
from app.services.token_budget_manager import TokenBudgetManager
from app.services.anomaly_detector import AnomalyDetector

logger = logging.getLogger(__name__)

class ChatService:
    """Service for handling chat operations with Advanced RAG"""
    
    def __init__(self):
        # In-memory conversation storage
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        
        self.llm_service = LLMService()
        
        # Security services
        self.injection_detector = PromptInjectionDetector()
        self.domain_classifier = DomainClassifier(
            self.llm_service,
            knowledge_base_description="Educational content from Python documentation"
        )
        
        # Fallback service
        self.fallback_service = FallbackService()
        
        # Restored services
        self.token_budget_manager = TokenBudgetManager()
        self.anomaly_detector = AnomalyDetector()
        
        # Advanced RAG services
        self.hybrid_rag = HybridRAGService()
        self.reranker = RerankingService()
        self.hallucination_detector = HallucinationDetector(
            self.llm_service, 
            self.hybrid_rag.fallback_embedding
        )
        self.pii_masker = PIIMasker()
        self.query_reformulator = QueryReformulator(self.llm_service)
        self.adaptive_router = AdaptiveRouter()
        self.retrieval_cache = RetrievalCache()
        self.multihop_retriever = MultiHopRetriever()
        self.bias_detector = EthicalBiasDetector()
        self.context_manager = ContextManager()
        self.secure_retrieval = SecureRetrievalService()

    async def process_chat(
        self, 
        message: str, 
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """Process a chat message and return AI response"""
        try:
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            self.conversations[conversation_id].append(user_message)
            
            ai_response = await self._generate_ai_response(
                message, 
                conversation_id, 
                context or {}
            )
            
            ai_message = {
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": "ai"
            }
            self.conversations[conversation_id].append(ai_message)
            
            return ChatResponse(
                response=ai_response,
                conversation_id=conversation_id,
                message_id=str(uuid.uuid4()),
                metadata={"tokens_used": len(ai_response.split())}
            )
            
        except Exception as e:
            logger.error(f"Error processing chat: {str(e)}")
            raise
    
    async def _generate_ai_response(
        self, 
        message: str, 
        conversation_id: str, 
        context: Dict[str, Any]
    ) -> str:
        """Generate AI response using Advanced RAG pipeline"""
        start_time = time.time()
        user_id = context.get('user_id', 'anonymous')
        user_role = context.get('user_role', 'student')
        
        try:
            # Token budget check
            budget_check = await self.token_budget_manager.check_budget(
                user_id=user_id,
                user_role=user_role,
                estimated_tokens=1000
            )
            
            if not budget_check['allowed']:
                return f"⚠️ {budget_check['message']}"
            
            # Security checks
            injection_result = await self.injection_detector.detect_injection(message)
            if injection_result['action'] == 'BLOCK':
                return self.injection_detector.get_safe_rejection_message()
            
            # PII masking
            masked_message = await self.pii_masker.mask_pii(message)
            query = masked_message['masked']
            
            # Query reformulation - FIXED VERSION
            conversation_history = self.get_conversation_history(conversation_id)
            reformulation_result = await self.query_reformulator.reformulate_query(
                query, 
                conversation_history
            )
            
            # CRITICAL: Extract the actual string from the dict result
            logger.info(f"Reformulation result type: {type(reformulation_result)}")
            logger.info(f"Reformulation result: {reformulation_result}")
            
            # Always extract the string value
            if isinstance(reformulation_result, dict):
                reformulated_query = reformulation_result.get('reformulated', query)
            else:
                reformulated_query = str(reformulation_result)
            
            # Double-check it's a string
            if not isinstance(reformulated_query, str):
                logger.error(f"reformulated_query is still not a string: {type(reformulated_query)}")
                reformulated_query = str(reformulated_query)
            
            logger.info(f"FINAL reformulated_query type: {type(reformulated_query)}")
            logger.info(f"FINAL reformulated_query value: {reformulated_query}")
            
            # Retrieval - this should now receive a string
            routing_decision = self.adaptive_router.analyze_query_complexity(reformulated_query)
            
            if routing_decision['strategy'] == 'fast_path':
                relevant_docs = await self.retrieval_cache.get_or_retrieve(
                    query=reformulated_query,
                    params={'conversation_id': conversation_id, 'top_k': 10},
                    retrieve_fn=lambda q, **kwargs: self.hybrid_rag.hybrid_search(q, top_k=10)
                )
            else:
                relevant_docs = await self.multihop_retriever.multi_hop_retrieve(
                    reformulated_query,
                    max_hops=2
                )
                relevant_docs = await self.reranker.rerank_results(
                    reformulated_query,
                    relevant_docs,
                    top_k=10
                )
            
            # Context optimization
            optimized_context_text = await self.context_manager.optimize_context(
                relevant_docs,
                reformulated_query
            )
            
            # Build messages
            settings = get_settings()
            domain_desc = getattr(settings, 'DOMAIN_DESCRIPTION', 'Software documentation and guides')
            system_prompt = (
                f"You are a strictly domain-specific AI assistant. Your domain is: {domain_desc}.\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. You MUST answer questions solely based on the provided Context.\n"
                "2. If the Context does not contain the answer, you must say: "
                "\"I cannot answer this as the information is not in my specific domain context.\"\n"
                "3. Do NOT use outside knowledge to answer questions, especially generic or out-of-domain questions."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            for msg in conversation_history[-5:]:
                messages.append({"role": msg.role, "content": msg.content})
            
            user_prompt = f"Context:\n{optimized_context_text}\n\nQuestion: {reformulated_query}"
            messages.append({"role": "user", "content": user_prompt})
            
            # Generate response
            try:
                response = await self.llm_service.generate_response(
                    messages,
                    temperature=0.7,
                    max_tokens=1000
                )
            except Exception as llm_error:
                logger.error(f"LLM error: {str(llm_error)}")
                response_result = await self.fallback_service.get_fallback_response(
                    reformulated_query,
                    conversation_history[-3:]
                )
                response = response_result.get('response', 'I apologize, but I encountered an error processing your request.')
            
            # Track usage
            tokens_used = len(response.split()) * 1.3
            await self.token_budget_manager.track_usage(
                user_id=user_id,
                tokens_used=int(tokens_used),
                model='gpt-4',
                request_type='completion'
            )
            
            # Anomaly detection
            anomaly_result = await self.anomaly_detector.analyze_request(
                user_id=user_id,
                tokens_used=int(tokens_used),
                cost=(tokens_used / 1000) * 0.03,
                request_metadata={'conversation_id': conversation_id}
            )
            
            if anomaly_result['is_anomaly'] and anomaly_result['action'] == 'block':
                return f"⛔ {anomaly_result['message']}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I apologize, but I encountered an error processing your request."
    
    def get_conversation_history(self, conversation_id: str) -> List[Message]:
        """Get conversation history"""
        if conversation_id not in self.conversations:
            return []
        
        messages = []
        for msg in self.conversations[conversation_id]:
            messages.append(Message(
                role=msg['role'],
                content=msg['content'],
                timestamp=msg.get('timestamp')
            ))
        
        return messages