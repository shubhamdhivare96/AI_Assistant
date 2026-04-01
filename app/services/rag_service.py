"""
RAG (Retrieval-Augmented Generation) Service
Embeddings: AWS Nova 2 (primary), Sentence Transformers (fallback)
"""
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import boto3
import json
from sentence_transformers import SentenceTransformer
import numpy as np
import uuid
from datetime import datetime
from app.config import get_settings
from app.core.connection_pool import get_qdrant_client, return_qdrant_client
from app.core.resilience import resilient_call, qdrant_breaker

logger = logging.getLogger(__name__)

class RAGService:
    """RAG Service for document retrieval and context augmentation"""
    
    def __init__(self):
        self.settings = get_settings()
        self.bedrock_client = None  # AWS Nova
        self.fallback_embedding = None  # Sentence Transformers
        self.qdrant_client = None
        self.embedding_dimensions = self.settings.EMBEDDING_DIMENSIONS
        # Don't initialize models immediately - use lazy loading
        self._models_initialized = False
        
    def _ensure_models_initialized(self):
        """Lazy initialization of models on first use"""
        if not self._models_initialized:
            self.initialize_models()
            self._models_initialized = True
        
    def initialize_models(self):
        """Initialize embedding models and Qdrant client"""
        try:
            # Primary: AWS Nova 2
            if self.settings.AWS_ACCESS_KEY_ID:
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
                    region_name=self.settings.AWS_REGION
                )
                logger.info("AWS Nova embedding initialized")
            
            # Fallback: Sentence Transformers
            self.fallback_embedding = SentenceTransformer(
                self.settings.FALLBACK_EMBEDDING_MODEL
            )
            logger.info("Fallback embedding initialized")
            
            # Get Qdrant client from connection pool
            self.qdrant_client = get_qdrant_client()
            
            # Create collection if it doesn't exist
            self._ensure_collection_exists()
            
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {str(e)}")
            raise
    
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists"""
        collections = self.qdrant_client.get_collections()
        collection_name = "documents"
        
        if collection_name not in [c.name for c in collections.collections]:
            self.qdrant_client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimensions,  # 1024 for Nova 2
                    distance=Distance.COSINE
                )
            )
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with fallback"""
        self._ensure_models_initialized()  # Lazy loading
        try:
            # Try primary (AWS Nova)
            return await self._generate_nova_embedding(text)
        except Exception as e:
            logger.warning(f"Nova embedding failed: {str(e)}, using fallback")
            # Fallback to Sentence Transformers
            embedding = self.fallback_embedding.encode(text).tolist()
            # Pad to 1024 dimensions if needed
            if len(embedding) < self.embedding_dimensions:
                embedding = embedding + [0.0] * (self.embedding_dimensions - len(embedding))
            return embedding[:self.embedding_dimensions]
    
    async def _generate_nova_embedding(self, text: str) -> List[float]:
        """Generate embedding using AWS Nova 2"""
        # Truncate if needed (max 8172 tokens)
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = self.settings.EMBEDDING_MAX_TOKENS * 4
        if len(text) > max_chars:
            text = text[:max_chars]
        
        response = self.bedrock_client.invoke_model(
            modelId=self.settings.EMBEDDING_MODEL,
            body=json.dumps({
                "inputText": text,
                "embeddingConfig": {
                    "outputEmbeddingLength": self.embedding_dimensions
                }
            })
        )
        
        result = json.loads(response['body'].read())
        return result['embedding']
    
    async def retrieve_relevant_context(
        self, 
        query: str, 
        conversation_id: str, 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query with resilience and parent-child support
        """
        @resilient_call(qdrant_breaker, max_retries=3)
        async def _search():
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Search in Qdrant (search on child chunks for precision)
            # qdrant-client >= 1.7: use query_points() instead of search()
            search_response = self.qdrant_client.query_points(
                collection_name="documents",
                query=query_embedding,
                limit=top_k * 2,  # Get more results to account for parent retrieval
                with_payload=True
            )
            search_result = search_response.points
            
            # Format results with parent-child handling
            results = []
            seen_parents = set()
            
            for hit in search_result:
                chunk_type = hit.payload.get('metadata', {}).get('chunk_type', 'simple')
                parent_id = hit.payload.get('metadata', {}).get('parent_id')
                
                # If this is a child chunk and we haven't seen its parent
                if chunk_type == 'child' and parent_id and parent_id not in seen_parents:
                    # Retrieve parent chunk for better context
                    parent_chunk = await self._get_parent_chunk(parent_id)
                    if parent_chunk:
                        results.append({
                            'text': parent_chunk['text'],
                            'score': hit.score,
                            'metadata': parent_chunk['metadata'],
                            'matched_child': hit.payload.get('text', '')
                        })
                        seen_parents.add(parent_id)
                elif chunk_type == 'parent':
                    # Use parent chunk directly
                    results.append({
                        'text': hit.payload.get('text', ''),
                        'score': hit.score,
                        'metadata': hit.payload.get('metadata', {})
                    })
                else:
                    # Simple chunk or standalone
                    results.append({
                        'text': hit.payload.get('text', ''),
                        'score': hit.score,
                        'metadata': hit.payload.get('metadata', {})
                    })
                
                if len(results) >= top_k:
                    break
            
            return results[:top_k]
        
        try:
            return await _search()
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []
    
    async def _get_parent_chunk(self, parent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve parent chunk by ID"""
        try:
            # Search for parent chunk by parent_id in metadata
            search_result = self.qdrant_client.scroll(
                collection_name="documents",
                scroll_filter={
                    "must": [
                        {
                            "key": "metadata.parent_id",
                            "match": {"value": parent_id}
                        },
                        {
                            "key": "metadata.chunk_type",
                            "match": {"value": "parent"}
                        }
                    ]
                },
                limit=1,
                with_payload=True
            )
            
            if search_result[0]:
                hit = search_result[0][0]
                return {
                    'text': hit.payload.get('text', ''),
                    'metadata': hit.payload.get('metadata', {})
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving parent chunk: {str(e)}")
            return None
    
    async def add_document(self, text: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store"""
        try:
            # Ensure models are initialized
            self._ensure_models_initialized()
            
            # Generate embedding
            embedding = self.fallback_embedding.encode(text).tolist()
            
            # Create point for Qdrant
            point_id = str(uuid.uuid4())
            point = {
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "text": text,
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Add to Qdrant
            self.qdrant_client.upsert(
                collection_name="documents",
                points=[point]
            )
            
            logger.info(f"Added document with ID: {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            raise
    
    async def search_similar(self, query: str, top_k: int = 5):
        """Search for similar documents"""
        try:
            # Ensure models are initialized
            self._ensure_models_initialized()
            
            # Generate query embedding
            query_embedding = self.fallback_embedding.encode(query).tolist()
            
            # Search in Qdrant
            # qdrant-client >= 1.7: use query_points() instead of search()
            search_response = self.qdrant_client.query_points(
                collection_name="documents",
                query=query_embedding,
                limit=top_k
            )
            
            return [
                {
                    'text': hit.payload.get('text', ''),
                    'score': hit.score,
                    'metadata': hit.payload.get('metadata', {})
                }
                for hit in search_response.points
            ]
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    async def retrieve_context(self, query: str, conversation_id: str = None):
        """Retrieve relevant context for a query"""
        # Get relevant documents
        similar_docs = await self.search_similar(query)
        
        # Format context
        context = "\n\n".join([
            f"Document {i+1}: {doc['text'][:500]}..." 
            for i, doc in enumerate(similar_docs)
        ])
        
        return {
            "context": context,
            "sources": similar_docs
        }
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Add multiple documents to the vector store"""
        # Ensure models are initialized
        self._ensure_models_initialized()
        
        points = []
        
        for doc in documents:
            embedding = self.fallback_embedding.encode(doc['text']).tolist()
            
            point = {
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": {
                    "text": doc['text'],
                    "metadata": doc.get('metadata', {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            points.append(point)
        
        # Batch upsert to Qdrant
        if points:
            self.qdrant_client.upsert(
                collection_name="documents",
                points=points
            )
    
    def get_collection_stats(self):
        """Get collection statistics"""
        try:
            collection_info = self.qdrant_client.get_collection("documents")
            return {
                "collection_name": "documents",
                "vectors_count": collection_info.vectors_count,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {"error": str(e)}
    
    async def delete_document(self, document_id: str):
        """Delete a document from the vector store"""
        try:
            self.qdrant_client.delete(
                collection_name="documents",
                points_selector=document_id
            )
            logger.info(f"Deleted document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False