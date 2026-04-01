"""
Database models for AI Assistant
NOTE: Learning and Quiz models removed as they are out of scope
Database models kept for conversation tracking (in-memory)
"""
from app.models.base import Base
from app.models.conversation import Conversation, Message, Document

__all__ = [
    "Base",
    "Conversation",
    "Message", 
    "Document"
]