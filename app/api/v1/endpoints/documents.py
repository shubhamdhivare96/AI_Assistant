"""
Document Management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional
import logging
import os
import shutil
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime

from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

logger = logging.getLogger(__name__)

# Pydantic models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    file_type: str
    conversation_id: Optional[str]
    user_id: Optional[str]
    status: str
    created_at: datetime
    processed: bool

# Dependency
def get_document_service() -> DocumentService:
    return DocumentService()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    service: DocumentService = Depends(get_document_service)
):
    """Upload a document"""
    try:
        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_location = os.path.join(upload_dir, file.filename)
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document
        document = await service.process_document(
            file_path=file_location,
            filename=file.filename,
            conversation_id=conversation_id,
            user_id=user_id
        )
        
        return document
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: DocumentService = Depends(get_document_service)
):
    """Get documents with optional filtering"""
    documents = await service.get_documents(
        conversation_id=conversation_id,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """Get a specific document"""
    document = await service.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    return document

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """Delete a document"""
    success = await service.delete_document(document_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )
    
    return {"message": "Document deleted successfully"}

@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """Get document content"""
    content = await service.get_document_content(document_id)
    
    if not content:
        raise HTTPException(
            status_code=404,
            detail="Document content not found"
        )
    
    return {"content": content}

@router.post("/{document_id}/index")
async def index_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service)
):
    """Index document for vector search"""
    success = await service.index_document(document_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to index document"
        )
    
    return {"message": "Document indexed successfully"}

@router.get("/search/", response_model=List[DocumentResponse])
async def search_documents(
    query: str = Query(..., min_length=1),
    user_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    service: DocumentService = Depends(get_document_service)
):
    """Search documents by filename"""
    results = await service.search_documents(query, user_id, limit)
    return results
