"""
Chat-related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    """Message role enum"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    """Message schema"""
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "role": "user",
                "content": "Hello, how are you?",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }

class ChatRequest(BaseModel):
    """Chat request schema"""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    user_id: Optional[str] = Field(None, description="User ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    stream: bool = Field(False, description="Whether to stream the response")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "What is the capital of France?",
                "conversation_id": "conv_123",
                "user_id": "user_123",
                "context": {"language": "en"},
                "stream": False
            }
        }

class ChatResponse(BaseModel):
    """Chat response schema"""
    response: str = Field(..., description="AI response")
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="Message ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "response": "The capital of France is Paris.",
                "conversation_id": "conv_123",
                "message_id": "msg_123",
                "timestamp": "2024-01-01T12:00:00Z",
                "metadata": {"tokens_used": 42}
            }
        }

class ChatHistory(BaseModel):
    """Chat history schema"""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[Message] = Field(default_factory=list, description="List of messages")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "conv_123",
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": "2024-01-01T12:00:00Z"},
                    {"role": "assistant", "content": "Hi there!", "timestamp": "2024-01-01T12:00:01Z"}
                ],
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }

class Conversation(BaseModel):
    """Conversation schema"""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    messages: List[Message] = Field(default_factory=list, description="List of messages")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "conv_123",
                "title": "Discussion about AI",
                "messages": [],
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "metadata": {"user_id": "user_123"}
            }
        }