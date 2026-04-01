"""
Conversation schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ConversationStatus(str, Enum):
    """Conversation status enum"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ConversationCreate(BaseModel):
    """Schema for creating a conversation"""
    title: str = Field(..., description="Conversation title", min_length=1, max_length=200)
    user_id: Optional[str] = Field(None, description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Discussion about AI",
                "user_id": "user_123",
                "metadata": {"topic": "artificial intelligence"}
            }
        }

class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = Field(None, description="Conversation title", min_length=1, max_length=200)
    is_archived: Optional[bool] = Field(None, description="Whether conversation is archived")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Updated conversation title",
                "is_archived": False,
                "metadata": {"updated": True}
            }
        }

class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    user_id: Optional[str] = Field(None, description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_archived: bool = Field(False, description="Whether conversation is archived")
    message_count: int = Field(0, description="Number of messages in conversation")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "conv_123",
                "title": "Discussion about AI",
                "user_id": "user_123",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "is_archived": False,
                "message_count": 10,
                "metadata": {"topic": "artificial intelligence"}
            }
        }

class ConversationListResponse(BaseModel):
    """Schema for conversation list response"""
    conversations: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    skip: int = Field(0, description="Number of conversations skipped")
    limit: int = Field(20, description="Maximum number of conversations returned")
    
    class Config:
        schema_extra = {
            "example": {
                "conversations": [
                    {
                        "id": "conv_123",
                        "title": "Discussion about AI",
                        "user_id": "user_123",
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "is_archived": False,
                        "message_count": 10
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 20
            }
        }

class ConversationMessage(BaseModel):
    """Schema for conversation message"""
    id: str = Field(..., description="Message ID")
    conversation_id: str = Field(..., description="Conversation ID")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "msg_123",
                "conversation_id": "conv_123",
                "role": "user",
                "content": "Hello, how are you?",
                "created_at": "2024-01-01T12:00:00Z",
                "metadata": {"tokens": 5}
            }
        }

class ConversationMessagesResponse(BaseModel):
    """Schema for conversation messages response"""
    messages: List[ConversationMessage] = Field(..., description="List of messages")
    conversation_id: str = Field(..., description="Conversation ID")
    total: int = Field(..., description="Total number of messages")
    skip: int = Field(0, description="Number of messages skipped")
    limit: int = Field(50, description="Maximum number of messages returned")
    
    class Config:
        schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": "msg_123",
                        "conversation_id": "conv_123",
                        "role": "user",
                        "content": "Hello",
                        "created_at": "2024-01-01T12:00:00Z"
                    }
                ],
                "conversation_id": "conv_123",
                "total": 1,
                "skip": 0,
                "limit": 50
            }
        }