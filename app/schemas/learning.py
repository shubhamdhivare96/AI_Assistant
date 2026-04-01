"""
Learning schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class QueryType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"

class QueryRequest(BaseModel):
    """Query request schema"""
    query: str = Field(..., description="User query")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    query_type: QueryType = Field(QueryType.TEXT, description="Type of query")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class AnswerResponse(BaseModel):
    """Answer response schema"""
    answer_id: str = Field(..., description="Answer ID")
    query_id: str = Field(..., description="Query ID")
    answer_text: str = Field(..., description="Answer text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuizQuestion(BaseModel):
    """Quiz question schema"""
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_items=2, description="Answer options")
    correct_answer: int = Field(..., ge=0, description="Index of correct answer (0-based)")
    explanation: Optional[str] = Field(None, description="Explanation of the answer")

class QuizRequest(BaseModel):
    """Quiz generation request"""
    topic: str = Field(..., description="Topic for quiz generation")
    difficulty: str = Field("medium", description="Difficulty level")
    num_questions: int = Field(5, ge=1, le=20, description="Number of questions")

class QuizResponse(BaseModel):
    """Quiz response schema"""
    quiz_id: str = Field(..., description="Quiz ID")
    topic: str = Field(..., description="Quiz topic")
    questions: List[QuizQuestion] = Field(..., description="Quiz questions")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuizQuestion(BaseModel):
    """Quiz question schema"""
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_items=2, description="Answer options")
    correct_answer: int = Field(..., ge=0, description="Index of correct answer")
    explanation: Optional[str] = Field(None, description="Explanation of the answer")

class QuizSubmission(BaseModel):
    """Quiz submission schema"""
    quiz_id: str = Field(..., description="Quiz ID")
    answers: List[int] = Field(..., description="User answers (0-based indices)")
    user_id: Optional[str] = Field(None, description="User ID")

class QuizResult(BaseModel):
    """Quiz result schema"""
    quiz_id: str = Field(..., description="Quiz ID")
    score: float = Field(..., ge=0, le=100, description="Score percentage")
    correct_answers: int = Field(..., description="Number of correct answers")
    total_questions: int = Field(..., description="Total questions")
    time_taken: Optional[float] = Field(None, description="Time taken in seconds")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

class EscalationRequest(BaseModel):
    """Escalation request schema"""
    query_id: str = Field(..., description="Query ID")
    reason: str = Field(..., description="Reason for escalation")
    priority: str = Field("medium", description="Priority level")
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

class EscalationResponse(BaseModel):
    """Escalation response schema"""
    escalation_id: str = Field(..., description="Escalation ID")
    query_id: str = Field(..., description="Query ID")
    status: str = Field(..., description="Escalation status")
    assigned_to: Optional[str] = Field(None, description="Assigned to (teacher/TA)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(None, description="When escalation was resolved")

class LearningProgress(BaseModel):
    """Learning progress schema"""
    user_id: str = Field(..., description="User ID")
    topic: str = Field(..., description="Learning topic")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    completed_quizzes: int = Field(0, description="Number of quizzes completed")
    average_score: float = Field(0.0, ge=0, le=100, description="Average quiz score")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    learning_goals: List[str] = Field(default_factory=list, description="Learning goals")

class FeedbackRequest(BaseModel):
    """Feedback submission schema"""
    answer_id: str = Field(..., description="Answer ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    feedback: Optional[str] = Field(None, description="Detailed feedback")
    helpful: Optional[bool] = Field(None, description="Was the answer helpful?")

class FeedbackResponse(BaseModel):
    """Feedback response schema"""
    feedback_id: str = Field(..., description="Feedback ID")
    answer_id: str = Field(..., description="Answer ID")
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None
    helpful: Optional[bool] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)