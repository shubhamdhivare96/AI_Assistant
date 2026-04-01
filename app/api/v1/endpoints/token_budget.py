"""
Token Budget Management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.services.token_budget_manager import TokenBudgetManager

router = APIRouter(prefix="/token-budget", tags=["token-budget"])

# Pydantic models
class UsageStats(BaseModel):
    daily_tokens: int
    monthly_tokens: int
    last_reset_daily: str
    last_reset_monthly: str
    history_count: int

class BudgetCheck(BaseModel):
    allowed: bool
    action: str = "allow"
    message: str
    daily_remaining: int
    monthly_remaining: int
    daily_usage_pct: float = 0.0
    monthly_usage_pct: float = 0.0

# Dependency
def get_token_budget_manager() -> TokenBudgetManager:
    return TokenBudgetManager()

@router.get("/{user_id}/stats", response_model=UsageStats)
async def get_usage_stats(
    user_id: str,
    manager: TokenBudgetManager = Depends(get_token_budget_manager)
):
    """Get token usage statistics for a user"""
    stats = await manager.get_usage_stats(user_id)
    return stats

@router.post("/{user_id}/check", response_model=BudgetCheck)
async def check_budget(
    user_id: str,
    user_role: str = Query("student"),
    estimated_tokens: int = Query(1000),
    manager: TokenBudgetManager = Depends(get_token_budget_manager)
):
    """Check if user has budget for a request"""
    result = await manager.check_budget(user_id, user_role, estimated_tokens)
    return result

@router.get("/all-users", response_model=List[Dict[str, Any]])
async def get_all_users_usage(
    manager: TokenBudgetManager = Depends(get_token_budget_manager)
):
    """Get usage for all users (admin only)"""
    usage = await manager.get_all_users_usage()
    return usage
