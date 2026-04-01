"""
Document schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    """Document type enum"""
    PDF = "pdf"
    TEXT = "text"
    WORD = "word"
    IMAGE = "image"
    OTHER = "other"

class DocumentUpload(BaseModel):
    """Schema for document upload"""
    filename: str = Field(..., description="Document filename")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "filename": "document.pdf",
                "conversation_id": "conv_123",
                "metadata": {"source": "upload"}
            }
        }

class DocumentResponse(BaseModel):
    """Schema for document response"""
    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Document filename")
    file_type: str = Field(..., description="Document type")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    processed: bool = Field(False, description="Whether document has been processed")
    vectorized: bool = Field(False, description="Whether document has been vectorized")
    created_at: datetime = Field(..., description="Creation timestamp")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "doc_123",
                "filename": "document.pdf",
                "file_type": "pdf",
                "file_size": 1024000,
                "processed": True,
                "vectorized": True,
                "created_at": "2024-01-01T12:00:00Z",
                "conversation_id": "conv_123",
                "metadata": {"pages": 10}
            }
        }

class DocumentListResponse(BaseModel):
    """Schema for document list response"""
    documents: List[DocumentResponse] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")
    skip: int = Field(0, description="Number of documents skipped")
    limit: int = Field(50, description="Maximum number of documents returned")
    
    class Config:
        schema_extra = {
            "example": {
                "documents": [
                    {
                        "id": "doc_123",
                        "filename": "document.pdf",
                        "file_type": "pdf",
                        "file_size": 1024000,
                        "processed": True,
                        "vectorized": True,
                        "created_at": "2024-01-01T12:00:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 50
            }
        }

class DocumentContentResponse(BaseModel):
    """Schema for document content response"""
    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Document filename")
    content: str = Field(..., description="Document content")
    content_preview: str = Field(..., description="First 500 characters of content")
    total_chars: int = Field(..., description="Total characters in content")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "doc_123",
                "filename": "document.pdf",
                "content": "This is the full document content...",
                "content_preview": "This is the full document content...",
                "total_chars": 1000
            }
        }

class DocumentProcessingRequest(BaseModel):
    """Schema for document processing request"""
    document_id: str = Field(..., description="Document ID")
    extract_text: bool = Field(True, description="Whether to extract text")
    generate_embeddings: bool = Field(True, description="Whether to generate embeddings")
    chunk_size: int = Field(1000, description="Text chunk size for embeddings")
    chunk_overlap: int = Field(200, description="Text chunk overlap")
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "doc_123",
                "extract_text": True,
                "generate_embeddings": True,
                "chunk_size": 1000,
                "chunk_overlap": 200
            }
        }

class DocumentProcessingResponse(BaseModel):
    """Schema for document processing response"""
    document_id: str = Field(..., description="Document ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Processing message")
    chunks_created: Optional[int] = Field(None, description="Number of text chunks created")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "doc_123",
                "status": "success",
                "message": "Document processed successfully",
                "chunks_created": 5,
                "processing_time_seconds": 2.5
            }
        }