"""
Conversation Management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])

# Pydantic models
class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

class MessageCreate(BaseModel):
    role: str
    content: str
    user_id: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    user_id: Optional[str]
    created_at: datetime

# Dependency
def get_conversation_service() -> ConversationService:
    return ConversationService()

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service)
):
    """Create a new conversation"""
    conversation = await service.create_conversation(
        user_id=request.user_id,
        title=request.title
    )
    return conversation

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Get a conversation by ID"""
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation

@router.get("/user/{user_id}", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    service: ConversationService = Depends(get_conversation_service)
):
    """Get conversations for a user"""
    conversations = await service.get_user_conversations(user_id, skip, limit)
    return conversations

@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    title: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Update a conversation"""
    conversation = await service.update_conversation(conversation_id, title)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Delete a conversation"""
    success = await service.delete_conversation(conversation_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or unauthorized"
        )
    return {"message": "Conversation deleted successfully"}

@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    service: ConversationService = Depends(get_conversation_service)
):
    """Add a message to a conversation"""
    try:
        msg = await service.add_message(
            conversation_id=conversation_id,
            role=message.role,
            content=message.content,
            user_id=message.user_id
        )
        return msg
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ConversationService = Depends(get_conversation_service)
):
    """Get messages for a conversation"""
    messages = await service.get_messages(conversation_id, skip, limit)
    return messages

@router.get("/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Get full conversation with messages"""
    history = await service.get_conversation_history(conversation_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return history

@router.get("/search/{user_id}", response_model=List[ConversationResponse])
async def search_conversations(
    user_id: str,
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    service: ConversationService = Depends(get_conversation_service)
):
    """Search conversations by title or content"""
    results = await service.search_conversations(user_id, query, limit)
    return results
