"""
Pydantic schemas for request/response validation
"""
from app.schemas.chat import ChatRequest, ChatResponse, Message, ChatHistory
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.schemas.document import DocumentUpload, DocumentResponse
# Learning and User schemas removed (not needed for core functionality)
# from app.schemas.learning import QueryRequest, AnswerResponse, QuizRequest, QuizResponse
# from app.schemas.user import UserCreate, UserUpdate, UserResponse

__all__ = [
    "ChatRequest",
    "ChatResponse", 
    "Message",
    "ChatHistory",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "DocumentUpload",
    "DocumentResponse"
]