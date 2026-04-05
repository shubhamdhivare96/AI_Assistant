"""
Chat endpoints
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from app.schemas.chat import ChatRequest, ChatResponse, Message, ChatHistory
from app.services.chat_service import ChatService
# Database removed - using in-memory storage
# from app.database import get_db
# from sqlalchemy.orm import Session

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message and return AI response (Legacy endpoint)
    """
    return await process_chat_message(request)

@router.post("/query", response_model=ChatResponse)
async def query(request: ChatRequest):
    """
    Process a chat message and return AI response (Assignment suggested endpoint)
    """
    return await process_chat_message(request)

async def process_chat_message(request: ChatRequest):
    """
    Unified chat message processing logic
    """
    try:
        chat_service = ChatService()
        response = await chat_service.process_chat(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        return response
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )
