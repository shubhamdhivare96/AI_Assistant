"""
Error Analysis Service
Analyzes errors and tracks patterns for system improvement
Uses in-memory storage instead of database
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class ErrorAnalyzer:
    """Analyze errors and track patterns"""
    
    def __init__(self):
        # In-memory storage instead of database
        self.error_store = []
        self.error_patterns = defaultdict(int)
        
    async def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        user_id: str = None
    ) -> Dict[str, Any]:
        """Log an error for analysis"""
        error_data = {
            "id": len(self.error_store) + 1,
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "resolved": False
        }
        
        self.error_store.append(error_data)
        self.error_patterns[error_type] += 1
        
        logger.info(f"Error logged: {error_type}")
        return error_data
    
    async def get_error_patterns(
        self,
        time_period: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """Get error patterns over time period"""
        cutoff_time = datetime.utcnow() - time_period
        
        recent_errors = [
            e for e in self.error_store
            if e['timestamp'] >= cutoff_time
        ]
        
        patterns = defaultdict(int)
        for error in recent_errors:
            patterns[error['error_type']] += 1
        
        return {
            "total_errors": len(recent_errors),
            "patterns": dict(patterns),
            "time_period": str(time_period)
        }
    
    async def get_frequent_errors(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most frequent errors"""
        sorted_patterns = sorted(
            self.error_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"error_type": error_type, "count": count}
            for error_type, count in sorted_patterns
        ]
    
    async def analyze_error_trends(
        self,
        time_period: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """Analyze error trends"""
        cutoff_time = datetime.utcnow() - time_period
        
        recent_errors = [
            e for e in self.error_store
            if e['timestamp'] >= cutoff_time
        ]
        
        # Group by day
        daily_errors = defaultdict(int)
        for error in recent_errors:
            day = error['timestamp'].date()
            daily_errors[day] += 1
        
        return {
            "total_errors": len(recent_errors),
            "daily_breakdown": {str(k): v for k, v in daily_errors.items()},
            "average_per_day": len(recent_errors) / max(time_period.days, 1)
        }
    
    async def get_unresolved_errors(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get unresolved errors"""
        unresolved = [
            e for e in self.error_store
            if not e.get('resolved', False)
        ]
        
        return sorted(
            unresolved,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    async def mark_error_resolved(
        self,
        error_id: int
    ) -> bool:
        """Mark an error as resolved"""
        for error in self.error_store:
            if error['id'] == error_id:
                error['resolved'] = True
                error['resolved_at'] = datetime.utcnow()
                return True
        return False
