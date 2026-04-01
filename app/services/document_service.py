"""
Document Service
Manages document upload and processing
Uses in-memory storage instead of database
"""
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for managing documents"""
    
    def __init__(self):
        # In-memory storage
        self.documents = {}
        
    async def process_document(
        self,
        file_path: str,
        filename: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process and store document metadata"""
        document_id = str(uuid.uuid4())
        
        # Get file info
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_ext = os.path.splitext(filename)[1]
        
        document = {
            "id": document_id,
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file_ext,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "status": "uploaded",
            "created_at": datetime.utcnow(),
            "processed": False
        }
        
        self.documents[document_id] = document
        
        logger.info(f"Document {filename} uploaded with ID {document_id}")
        return document
    
    async def get_document(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        return self.documents.get(document_id)
    
    async def get_documents(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get documents with filters"""
        filtered_docs = list(self.documents.values())
        
        if conversation_id:
            filtered_docs = [d for d in filtered_docs if d.get('conversation_id') == conversation_id]
        
        if user_id:
            filtered_docs = [d for d in filtered_docs if d.get('user_id') == user_id]
        
        # Sort by created_at
        filtered_docs.sort(key=lambda x: x['created_at'], reverse=True)
        
        return filtered_docs[skip:skip+limit]
    
    async def delete_document(
        self,
        document_id: str
    ) -> bool:
        """Delete a document"""
        if document_id not in self.documents:
            return False
        
        document = self.documents[document_id]
        
        # Delete file if exists
        if os.path.exists(document['file_path']):
            try:
                os.remove(document['file_path'])
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
        
        # Remove from storage
        del self.documents[document_id]
        
        logger.info(f"Deleted document {document_id}")
        return True
    
    async def update_document_status(
        self,
        document_id: str,
        status: str,
        processed: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Update document processing status"""
        if document_id not in self.documents:
            return None
        
        document = self.documents[document_id]
        document['status'] = status
        document['processed'] = processed
        document['updated_at'] = datetime.utcnow()
        
        logger.info(f"Updated document {document_id} status to {status}")
        return document
    
    async def get_document_content(
        self,
        document_id: str
    ) -> Optional[str]:
        """Get document content"""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        file_path = document['file_path']
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading document: {e}")
            return None
    
    async def index_document(
        self,
        document_id: str
    ) -> bool:
        """Index document for search (placeholder)"""
        document = self.documents.get(document_id)
        if not document:
            return False
        
        # Placeholder for indexing logic
        # In a real system, this would:
        # 1. Extract text from document
        # 2. Generate embeddings
        # 3. Store in vector database
        
        document['indexed'] = True
        document['indexed_at'] = datetime.utcnow()
        
        logger.info(f"Indexed document {document_id}")
        return True
    
    async def search_documents(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search documents by filename"""
        query_lower = query.lower()
        
        matching_docs = []
        for doc in self.documents.values():
            if user_id and doc.get('user_id') != user_id:
                continue
            
            if query_lower in doc['filename'].lower():
                matching_docs.append(doc)
        
        # Sort by created_at
        matching_docs.sort(key=lambda x: x['created_at'], reverse=True)
        
        return matching_docs[:limit]
