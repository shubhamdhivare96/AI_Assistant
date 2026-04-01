"""
Learning endpoints
NOTE: Placeholder for future learning features
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/learning", tags=["learning"])

# Pydantic models
class LearningResponse(BaseModel):
    message: str
    status: str

@router.get("/", response_model=LearningResponse)
async def get_learning_status():
    """Get learning system status"""
    return {
        "message": "Learning features are planned for future implementation",
        "status": "not_implemented"
    }

@router.post("/feedback", response_model=LearningResponse)
async def submit_learning_feedback(
    query: str,
    response: str,
    rating: int
):
    """Submit feedback for learning (placeholder)"""
    # This would integrate with the fine-tuning pipeline
    return {
        "message": "Feedback received (placeholder)",
        "status": "accepted"
    }
