"""
Conversation Service
Manages conversations and messages
Uses in-memory storage instead of database
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversations"""
    
    def __init__(self):
        # In-memory storage
        self.conversations = {}
        self.messages = {}
        
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        
        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "title": title or "New Conversation",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 0
        }
        
        self.conversations[conversation_id] = conversation
        self.messages[conversation_id] = []
        
        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return conversation
    
    async def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        return self.conversations.get(conversation_id)
    
    async def get_user_conversations(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get conversations for a user"""
        user_conversations = [
            conv for conv in self.conversations.values()
            if conv['user_id'] == user_id
        ]
        
        # Sort by updated_at
        user_conversations.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return user_conversations[skip:skip+limit]
    
    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a conversation"""
        if conversation_id not in self.conversations:
            return None
        
        conversation = self.conversations[conversation_id]
        
        if title:
            conversation['title'] = title
        
        conversation['updated_at'] = datetime.utcnow()
        
        logger.info(f"Updated conversation {conversation_id}")
        return conversation
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Delete a conversation"""
        if conversation_id not in self.conversations:
            return False
        
        conversation = self.conversations[conversation_id]
        
        # Verify ownership
        if conversation['user_id'] != user_id:
            logger.warning(f"User {user_id} attempted to delete conversation {conversation_id} owned by {conversation['user_id']}")
            return False
        
        # Delete conversation and messages
        del self.conversations[conversation_id]
        if conversation_id in self.messages:
            del self.messages[conversation_id]
        
        logger.info(f"Deleted conversation {conversation_id}")
        return True
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a message to a conversation"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        message_id = str(uuid.uuid4())
        
        message = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }
        
        self.messages[conversation_id].append(message)
        
        # Update conversation
        conversation = self.conversations[conversation_id]
        conversation['message_count'] += 1
        conversation['updated_at'] = datetime.utcnow()
        
        logger.info(f"Added message to conversation {conversation_id}")
        return message
    
    async def get_messages(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        if conversation_id not in self.messages:
            return []
        
        messages = self.messages[conversation_id]
        return messages[skip:skip+limit]
    
    async def get_conversation_history(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get full conversation with messages"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        messages = await self.get_messages(conversation_id)
        
        return {
            **conversation,
            "messages": messages
        }
    
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search conversations by title or content"""
        query_lower = query.lower()
        
        matching_conversations = []
        
        for conv in self.conversations.values():
            if conv['user_id'] != user_id:
                continue
            
            # Search in title
            if query_lower in conv['title'].lower():
                matching_conversations.append(conv)
                continue
            
            # Search in messages
            conv_messages = self.messages.get(conv['id'], [])
            for msg in conv_messages:
                if query_lower in msg['content'].lower():
                    matching_conversations.append(conv)
                    break
        
        # Sort by updated_at
        matching_conversations.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return matching_conversations[:limit]
