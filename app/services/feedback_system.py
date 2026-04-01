"""
Feedback Collection System
Collects and analyzes user feedback (without clarification loop)
Uses in-memory storage instead of database
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class FeedbackSystem:
    """Collect and analyze user feedback"""
    
    def __init__(self):
        # In-memory storage
        self.feedback_store = []
        
    async def collect_feedback(
        self, 
        message_id: str, 
        feedback_type: str,
        rating: Optional[int] = None, 
        comment: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collect user feedback on responses
        
        feedback_type: "thumbs_up", "thumbs_down", "rating"
        rating: 1-5 stars (optional)
        comment: free text feedback (optional)
        """
        feedback_data = {
            "id": len(self.feedback_store) + 1,
            "message_id": message_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "comment": comment,
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        }
        
        # Store in memory
        self.feedback_store.append(feedback_data)
        
        logger.info(f"Collected feedback: {feedback_type} for message {message_id}")
        return feedback_data
    
    async def get_low_satisfaction_queries(
        self, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get queries with low satisfaction for fine-tuning
        Uses in-memory feedback store
        """
        low_satisfaction = [
            f for f in self.feedback_store
            if f.get('rating', 5) < 3 or f.get('feedback_type') == 'thumbs_down'
        ][:limit]
        
        logger.info(f"Retrieved {len(low_satisfaction)} low satisfaction queries")
        return low_satisfaction
    
    async def analyze_feedback_trends(
        self, 
        time_period: str = "week"
    ) -> Dict[str, Any]:
        """
        Analyze feedback trends over time period
        Uses in-memory feedback store
        """
        total = len(self.feedback_store)
        positive = sum(1 for f in self.feedback_store if f.get('feedback_type') == 'thumbs_up' or f.get('rating', 0) >= 4)
        negative = sum(1 for f in self.feedback_store if f.get('feedback_type') == 'thumbs_down' or f.get('rating', 0) < 3)
        
        ratings = [f.get('rating', 0) for f in self.feedback_store if f.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        stats = {
            "total_feedback": total,
            "positive_feedback": positive,
            "negative_feedback": negative,
            "avg_rating": avg_rating,
            "satisfaction_rate": positive / total if total > 0 else 0
        }
        
        return stats
    
    async def get_feedback_by_message(
        self,
        message_id: str
    ) -> List[Dict[str, Any]]:
        """Get all feedback for a specific message"""
        return [
            f for f in self.feedback_store
            if f['message_id'] == message_id
        ]
    
    async def get_user_feedback_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get feedback history for a user"""
        user_feedback = [
            f for f in self.feedback_store
            if f.get('user_id') == user_id
        ]
        
        return sorted(
            user_feedback,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    async def generate_improvement_suggestions(
        self, 
        feedback_data: List[Dict] = None
    ) -> List[str]:
        """
        Generate improvement suggestions based on feedback
        """
        if feedback_data is None:
            feedback_data = self.feedback_store
        
        suggestions = []
        
        # Analyze common themes in negative feedback
        negative_comments = [
            f['comment'] 
            for f in feedback_data 
            if f.get('rating', 5) < 3 and f.get('comment')
        ]
        
        if negative_comments:
            # Simple analysis (could be enhanced with LLM)
            common_words = defaultdict(int)
            for comment in negative_comments:
                words = comment.lower().split()
                for word in words:
                    if len(word) > 4:
                        common_words[word] += 1
            
            top_issues = sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:5]
            
            suggestions = [
                f"Address issues related to: {word} (mentioned {count} times)"
                for word, count in top_issues
            ]
        
        return suggestions
    
    async def get_feedback_stats(self) -> Dict[str, Any]:
        """Get overall feedback statistics"""
        if not self.feedback_store:
            return {
                'total': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'avg_rating': 0
            }
        
        positive = sum(1 for f in self.feedback_store if f.get('feedback_type') == 'thumbs_up' or f.get('rating', 0) >= 4)
        negative = sum(1 for f in self.feedback_store if f.get('feedback_type') == 'thumbs_down' or f.get('rating', 0) < 3)
        neutral = len(self.feedback_store) - positive - negative
        
        ratings = [f.get('rating', 0) for f in self.feedback_store if f.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            'total': len(self.feedback_store),
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'avg_rating': avg_rating,
            'satisfaction_rate': positive / len(self.feedback_store) if self.feedback_store else 0
        }
