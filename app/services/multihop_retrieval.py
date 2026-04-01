"""
Multi-Hop Retrieval Service
"""
import logging
from typing import List, Dict, Any, Optional
from app.services.hybrid_rag_service import HybridRAGService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class MultiHopRetriever:
    """Multi-hop retrieval for complex queries"""
    
    def __init__(self):
        self.hybrid_rag = HybridRAGService()
        self.llm_service = LLMService()
        self.max_hops = 3
    
    async def multi_hop_retrieve(
        self, 
        query: str, 
        max_hops: int = 3,
        top_k_per_hop: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Iteratively retrieve evidence, building context across hops
        """
        all_evidence = []
        current_query = query
        seen_docs = set()
        
        for hop in range(max_hops):
            logger.info(f"Multi-hop retrieval - Hop {hop + 1}/{max_hops}")
            
            # Retrieve for current query
            results = await self.hybrid_rag.hybrid_search(
                current_query, 
                top_k=top_k_per_hop
            )
            
            # Deduplicate and add to evidence
            new_results = []
            for result in results:
                doc_hash = hash(result['text'][:100])  # Hash first 100 chars
                if doc_hash not in seen_docs:
                    seen_docs.add(doc_hash)
                    new_results.append(result)
                    all_evidence.append({
                        **result,
                        'hop': hop + 1,
                        'query': current_query
                    })
            
            if not new_results:
                logger.info(f"No new results at hop {hop + 1}, stopping early")
                break
            
            # Analyze gaps in evidence
            gaps = await self._identify_knowledge_gaps(query, all_evidence)
            
            if not gaps:
                logger.info(f"Sufficient evidence collected at hop {hop + 1}")
                break
            
            # Formulate follow-up query for next hop
            if hop < max_hops - 1:
                current_query = await self._formulate_followup_query(query, gaps)
                logger.info(f"Follow-up query for hop {hop + 2}: {current_query}")
        
        # Deduplicate and rerank all evidence
        final_results = await self._deduplicate_and_rerank(query, all_evidence)
        
        logger.info(f"Multi-hop retrieval complete: {len(final_results)} unique documents")
        return final_results[:10]  # Return top 10
    
    async def _identify_knowledge_gaps(
        self, 
        original_query: str, 
        evidence: List[Dict]
    ) -> List[str]:
        """
        Identify what information is missing from current evidence
        """
        evidence_text = "\n".join([doc['text'][:200] for doc in evidence[:5]])
        
        prompt = f"""
        Analyze if the following evidence is sufficient to answer the query.
        
        Query: {original_query}
        
        Evidence:
        {evidence_text}
        
        List any missing information or concepts needed to fully answer the query.
        If evidence is sufficient, respond with "SUFFICIENT".
        Keep response brief (max 3 gaps).
        """
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.llm_service.generate_response(
                messages, 
                temperature=0.1, 
                max_tokens=200
            )
            
            if "SUFFICIENT" in response.upper():
                return []
            
            # Extract gaps (simple line-based parsing)
            gaps = [
                line.strip() 
                for line in response.split('\n') 
                if line.strip() and not line.strip().startswith('#')
            ]
            
            return gaps[:3]  # Max 3 gaps
            
        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {str(e)}")
            return []
    
    async def _formulate_followup_query(
        self, 
        original_query: str, 
        gaps: List[str]
    ) -> str:
        """
        Formulate follow-up query to address knowledge gaps
        """
        gaps_text = "\n".join(f"- {gap}" for gap in gaps)
        
        prompt = f"""
        Original query: {original_query}
        
        Missing information:
        {gaps_text}
        
        Formulate a focused search query to find the missing information.
        Keep it concise (max 15 words).
        """
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        try:
            followup = await self.llm_service.generate_response(
                messages, 
                temperature=0.2, 
                max_tokens=50
            )
            
            return followup.strip()
            
        except Exception as e:
            logger.error(f"Error formulating follow-up query: {str(e)}")
            return original_query  # Fallback to original
    
    async def _deduplicate_and_rerank(
        self, 
        query: str, 
        evidence: List[Dict]
    ) -> List[Dict]:
        """
        Deduplicate evidence and rerank by relevance
        """
        # Simple deduplication by text similarity
        unique_evidence = []
        seen_texts = set()
        
        for doc in evidence:
            text_hash = hash(doc['text'][:200])
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_evidence.append(doc)
        
        # Sort by score (already computed during retrieval)
        sorted_evidence = sorted(
            unique_evidence, 
            key=lambda x: x.get('score', 0), 
            reverse=True
        )
        
        return sorted_evidence
    
    async def explain_retrieval_path(
        self, 
        results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Explain the multi-hop retrieval path
        """
        hops = {}
        for result in results:
            hop_num = result.get('hop', 1)
            if hop_num not in hops:
                hops[hop_num] = []
            hops[hop_num].append({
                'text': result['text'][:100] + '...',
                'score': result.get('score', 0),
                'query': result.get('query', '')
            })
        
        return {
            "total_hops": len(hops),
            "hops": hops,
            "total_documents": len(results)
        }
