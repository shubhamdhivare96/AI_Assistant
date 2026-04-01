"""
Conversation models
NOTE: SQLAlchemy models kept for future database integration
Currently not used (system uses in-memory storage)
"""
from datetime import datetime
from typing import Optional, List

# SQLAlchemy imports commented out - not currently used
# from sqlalchemy import Integer, String, Text, Boolean, ForeignKey
# from sqlalchemy.orm import Mapped, mapped_column, relationship
# from app.models.base import Base, TimestampMixin

# Conversation model for future database use
# class Conversation(Base, TimestampMixin):
#     """Conversation model"""
#     __tablename__ = "conversations"
#     
#     id: Mapped[str] = mapped_column(String(36), primary_key=True)
#     user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
#     title: Mapped[str] = mapped_column(String(255), nullable=False)
#     
#     # Relationships
#     messages: Mapped[List["Message"]] = relationship(
#         "Message",
#         back_populates="conversation",
#         cascade="all, delete-orphan"
#     )

# Message model for future database use
# class Message(Base, TimestampMixin):
#     """Message model"""
#     __tablename__ = "messages"
#     
#     id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
#     conversation_id: Mapped[str] = mapped_column(
#         String(36),
#         ForeignKey("conversations.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )
#     role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
#     content: Mapped[str] = mapped_column(Text, nullable=False)
#     user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
#     
#     # Relationships
#     conversation: Mapped["Conversation"] = relationship(
#         "Conversation",
#         back_populates="messages"
#     )

# Placeholder classes for in-memory use
class Conversation:
    """In-memory conversation representation"""
    def __init__(self, id: str, user_id: str, title: str):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.messages = []

class Message:
    """In-memory message representation"""
    def __init__(self, conversation_id: str, role: str, content: str, user_id: Optional[str] = None):
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.user_id = user_id
        self.created_at = datetime.utcnow()
