"""
Token Budget Manager
Tracks and manages token usage per user with budget limits
Uses in-memory storage instead of database and Redis
"""
import logging
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class TokenBudgetManager:
    """Manage token budgets and usage tracking"""
    
    def __init__(self):
        # In-memory storage instead of database
        self.usage_store = defaultdict(lambda: {
            'daily_tokens': 0,
            'monthly_tokens': 0,
            'last_reset_daily': datetime.utcnow().date(),
            'last_reset_monthly': datetime.utcnow().replace(day=1).date(),
            'history': []
        })
        
        # Budget limits by role
        self.budgets = {
            'student': {'daily': 50000, 'monthly': 1000000},
            'teacher': {'daily': 200000, 'monthly': 5000000},
            'admin': {'daily': 1000000, 'monthly': 20000000},
            'premium': {'daily': 500000, 'monthly': 10000000},
            'free': {'daily': 10000, 'monthly': 200000}
        }
        
        self.soft_threshold = 0.8  # Warn at 80%
    
    async def check_budget(
        self,
        user_id: str,
        user_role: str = 'student',
        estimated_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Check if user has budget for request"""
        # Reset counters if needed
        self._reset_counters_if_needed(user_id)
        
        usage = self.usage_store[user_id]
        budget = self.budgets.get(user_role, self.budgets['student'])
        
        # Check daily budget
        daily_remaining = budget['daily'] - usage['daily_tokens']
        monthly_remaining = budget['monthly'] - usage['monthly_tokens']
        
        if daily_remaining < estimated_tokens:
            return {
                'allowed': False,
                'reason': 'daily_limit_exceeded',
                'message': f"Daily token limit exceeded. Limit: {budget['daily']}, Used: {usage['daily_tokens']}",
                'daily_remaining': 0,
                'monthly_remaining': monthly_remaining
            }
        
        if monthly_remaining < estimated_tokens:
            return {
                'allowed': False,
                'reason': 'monthly_limit_exceeded',
                'message': f"Monthly token limit exceeded. Limit: {budget['monthly']}, Used: {usage['monthly_tokens']}",
                'daily_remaining': daily_remaining,
                'monthly_remaining': 0
            }
        
        # Check soft threshold
        daily_usage_pct = usage['daily_tokens'] / budget['daily']
        monthly_usage_pct = usage['monthly_tokens'] / budget['monthly']
        
        action = 'allow'
        message = 'Budget available'
        
        if daily_usage_pct >= self.soft_threshold:
            action = 'warn'
            message = f"Warning: {daily_usage_pct*100:.1f}% of daily budget used"
        elif monthly_usage_pct >= self.soft_threshold:
            action = 'warn'
            message = f"Warning: {monthly_usage_pct*100:.1f}% of monthly budget used"
        
        return {
            'allowed': True,
            'action': action,
            'message': message,
            'daily_remaining': daily_remaining,
            'monthly_remaining': monthly_remaining,
            'daily_usage_pct': daily_usage_pct,
            'monthly_usage_pct': monthly_usage_pct
        }
    
    async def track_usage(
        self,
        user_id: str,
        tokens_used: int,
        model: str = 'gpt-4',
        request_type: str = 'completion'
    ) -> Dict[str, Any]:
        """Track token usage"""
        # Reset counters if needed
        self._reset_counters_if_needed(user_id)
        
        usage = self.usage_store[user_id]
        
        # Update counters
        usage['daily_tokens'] += tokens_used
        usage['monthly_tokens'] += tokens_used
        
        # Add to history
        usage['history'].append({
            'timestamp': datetime.utcnow(),
            'tokens': tokens_used,
            'model': model,
            'request_type': request_type
        })
        
        # Keep only last 1000 entries
        if len(usage['history']) > 1000:
            usage['history'] = usage['history'][-1000:]
        
        logger.info(f"Tracked {tokens_used} tokens for user {user_id}")
        
        return {
            'daily_total': usage['daily_tokens'],
            'monthly_total': usage['monthly_tokens'],
            'tokens_added': tokens_used
        }
    
    async def get_usage_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get usage statistics for user"""
        self._reset_counters_if_needed(user_id)
        
        usage = self.usage_store[user_id]
        
        return {
            'daily_tokens': usage['daily_tokens'],
            'monthly_tokens': usage['monthly_tokens'],
            'last_reset_daily': usage['last_reset_daily'].isoformat(),
            'last_reset_monthly': usage['last_reset_monthly'].isoformat(),
            'history_count': len(usage['history'])
        }
    
    async def get_all_users_usage(self) -> List[Dict[str, Any]]:
        """Get usage for all users"""
        result = []
        for user_id, usage in self.usage_store.items():
            self._reset_counters_if_needed(user_id)
            result.append({
                'user_id': user_id,
                'daily_tokens': usage['daily_tokens'],
                'monthly_tokens': usage['monthly_tokens']
            })
        return result
    
    def _reset_counters_if_needed(self, user_id: str):
        """Reset daily/monthly counters if needed"""
        usage = self.usage_store[user_id]
        today = datetime.utcnow().date()
        this_month = datetime.utcnow().replace(day=1).date()
        
        # Reset daily counter
        if usage['last_reset_daily'] < today:
            usage['daily_tokens'] = 0
            usage['last_reset_daily'] = today
        
        # Reset monthly counter
        if usage['last_reset_monthly'] < this_month:
            usage['monthly_tokens'] = 0
            usage['last_reset_monthly'] = this_month
