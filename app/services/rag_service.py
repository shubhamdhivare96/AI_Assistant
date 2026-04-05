"""
RAG (Retrieval-Augmented Generation) Service
Embeddings: AWS Nova 2 (primary), Sentence Transformers (fallback)
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import boto3
import json
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
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
        self.sparse_embedding = None  # FastEmbed Sparse
        self.qdrant_client = None
        self.embedding_dimensions = self.settings.EMBEDDING_DIMENSIONS
        # Don't initialize models immediately - use lazy loading
        self._models_initialized = False
        
    def _ensure_models_initialized(self):
        """Lazy initialization of models on first use"""
        if not self._models_initialized:
            self.initialize_models()
            self._models_initialized = True

    async def initialize(self):
        """Pre-load models for startup"""
        self._ensure_models_initialized()
        
    def initialize_models(self):
        """Initialize embedding models and Qdrant client"""
        try:
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(
                url=self.settings.QDRANT_URL,
                api_key=self.settings.QDRANT_API_KEY,
                timeout=120,
                prefer_grpc=False  # Reverting to HTTP for better stability in this environment
            )

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
            
            # Sparse: FastEmbed (BGE-M3)
            self.sparse_embedding = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")
            logger.info("Sparse embedding (Splade) initialized")
            
            # Get Qdrant client from connection pool
            self.qdrant_client = get_qdrant_client()
            
            # Create collection if it doesn't exist
            self._ensure_collection_exists()
            
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {str(e)}")
            raise
    
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists with Hybrid support (with retries for network stability)"""
        from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                collections = self.qdrant_client.get_collections()
                collection_name = "documents"
                
                # Check if collection needs recreation (if it doesn't have sparse config)
                exists = collection_name in [c.name for c in collections.collections]
                needs_recreate = False
                
                if exists:
                    info = self.qdrant_client.get_collection(collection_name)
                    if not info.config.params.sparse_vectors:
                        needs_recreate = True
                        logger.warning(f"Collection {collection_name} exists but lacks sparse vector support. Recreating...")

                if not exists or needs_recreate:
                    if exists:
                        self.qdrant_client.delete_collection(collection_name)
                    
                    self.qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config={
                            "text-dense": VectorParams(
                                size=self.embedding_dimensions,
                                distance=Distance.COSINE
                            )
                        },
                        sparse_vectors_config={
                            "text-sparse": SparseVectorParams()
                        }
                    )
                    logger.info(f"Collection {collection_name} created with Hybrid support (text-dense + text-sparse)")
                return # Success
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to connect to Qdrant after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Qdrant connection attempt {attempt+1} failed: {e}. Retrying...")
                import time
                time.sleep(2)
    
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
    
    def _invoke_bedrock_model(self, text: str):
        """Blocking call to Bedrock - run in thread"""
        response = self.bedrock_client.invoke_model(
            modelId=self.settings.EMBEDDING_MODEL,
            body=json.dumps({
                "inputText": text,
                "embeddingConfig": {
                    "outputEmbeddingLength": self.embedding_dimensions
                }
            })
        )
        return json.loads(response['body'].read())

    async def _generate_nova_embedding(self, text: str) -> List[float]:
        """Generate Bedrock embedding (threaded for concurrency)"""
        # Truncate if needed (max 8172 tokens)
        max_chars = self.settings.EMBEDDING_MAX_TOKENS * 4
        if len(text) > max_chars:
            text = text[:max_chars]
        
        try:
            result = await asyncio.to_thread(self._invoke_bedrock_model, text)
            return result['embedding']
        except Exception as e:
            logger.error(f"Bedrock invocation failed: {str(e)}")
            raise
    
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
        """Add a document with both Dense and Sparse vectors for Hybrid search"""
        try:
            self._ensure_models_initialized()
            
            # Generate Dense Embedding
            dense_vector = await self._generate_embedding(text)
            
            # Generate Sparse Embedding (FastEmbed)
            # .embed returns a generator, we take the first (and only) one
            sparse_vector = list(self.sparse_embedding.embed([text]))[0]
            
            # Prepare Point
            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector={
                    "text-dense": dense_vector,
                    "text-sparse": {
                        "indices": sparse_vector.indices.tolist(),
                        "values": sparse_vector.values.tolist()
                    }
                },
                payload={
                    "text": text,
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Upsert
            self.qdrant_client.upsert(
                collection_name="documents",
                points=[point]
            )
            
            logger.info(f"Added hybrid document: {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            raise

    async def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = 10):
        """Batch add documents with Hybrid vectors using concurrent memory batches and retries"""
        self._ensure_models_initialized()
        
        # Process in smaller batches to avoid memory overflow (Splade is memory-intensive)
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            
            # Retry logic for network stability
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    points = []
                    
                    # Batch generate sparse embeddings for this small window (Splade)
                    texts = [doc['text'] for doc in batch]
                    sparse_vectors_gen = self.sparse_embedding.embed(texts)
                    sparse_vectors = list(sparse_vectors_gen)
                    
                    # Generate Dense embeddings concurrently (Bedrock)
                    dense_tasks = [self._generate_embedding(text) for text in texts]
                    dense_vectors = await asyncio.gather(*dense_tasks)
                    
                    for j, doc in enumerate(batch):
                        dense_vector = dense_vectors[j]
                        sparse_vector = sparse_vectors[j]
                        
                        point = PointStruct(
                            id=str(uuid.uuid4()),
                            vector={
                                "text-dense": dense_vector,
                                "text-sparse": {
                                    "indices": sparse_vector.indices.tolist(),
                                    "values": sparse_vector.values.tolist()
                                }
                            },
                            payload={
                                "text": doc['text'],
                                "metadata": doc.get('metadata', {}),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        points.append(point)
                    
                    if points:
                        self.qdrant_client.upsert(
                            collection_name="documents",
                            points=points
                        )
                    break # Success!
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to ingest batch after {max_retries} attempts: {e}")
                        raise
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Batch ingestion attempt {attempt+1} failed: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

            logger.info(f"Ingested batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        
        logger.info(f"Total hybrid documents indexed: {len(documents)}")

    async def search_similar(self, query: str, top_k: int = 5, alpha: float = 0.5):
        """Hybrid search (Dense + Sparse) using Qdrant Prefetch & Fusion"""
        try:
            self._ensure_models_initialized()
            from qdrant_client.http import models
            
            # 1. Generate Query Vectors
            dense_vector = await self._generate_embedding(query)
            sparse_vector = list(self.sparse_embedding.embed([query]))[0]
            
            # 2. Hybrid Search with Fusion
            # We use prefetches for both dense and sparse, then fuse them
            search_response = self.qdrant_client.query_points(
                collection_name="documents",
                prefetch=[
                    models.Prefetch(
                        query=dense_vector,
                        using="text-dense",
                        limit=top_k * 2
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_vector.indices.tolist(),
                            values=sparse_vector.values.tolist()
                        ),
                        using="text-sparse",
                        limit=top_k * 2
                    )
                ],
                # RRF is generally better for hybrid than score addition
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
                with_payload=True
            )
            
            return [
                {
                    'text': hit.payload.get('text', ''),
                    'score': hit.score,
                    'metadata': hit.payload.get('metadata', {}),
                    'retrieval_id': hit.id
                }
                for hit in search_response.points
            ]
            
        except Exception as e:
            logger.error(f"Error in hybrid search_similar: {str(e)}")
            return []

    async def retrieve_context(self, query: str, conversation_id: str = None):
        """Retrieve relevant context for a query using Hybrid search"""
        similar_docs = await self.search_similar(query)
        
        context = "\n\n".join([
            f"Document {i+1}: {doc['text']}" 
            for i, doc in enumerate(similar_docs)
        ])
        
        return {
            "context": context,
            "sources": similar_docs
        }
    
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