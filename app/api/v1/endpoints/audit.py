"""
Audit Log endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/audit", tags=["audit"])

# Pydantic models
class AuditLogEntry(BaseModel):
    id: int
    timestamp: datetime
    action_type: str
    user_id: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    details: dict
    ip_address: Optional[str]
    user_agent: Optional[str]

# Dependency
def get_audit_logger() -> AuditLogger:
    return AuditLogger()

@router.get("/logs", response_model=List[AuditLogEntry])
async def get_logs(
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    logger: AuditLogger = Depends(get_audit_logger)
):
    """Get audit logs with filters"""
    logs = await logger.get_logs(user_id, action_type, resource_type, limit)
    return logs

@router.get("/user/{user_id}", response_model=List[AuditLogEntry])
async def get_user_activity(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    logger: AuditLogger = Depends(get_audit_logger)
):
    """Get activity for a specific user"""
    activity = await logger.get_user_activity(user_id, limit)
    return activity

@router.get("/security", response_model=List[AuditLogEntry])
async def get_security_events(
    limit: int = Query(100, ge=1, le=1000),
    logger: AuditLogger = Depends(get_audit_logger)
):
    """Get security-related events"""
    events = await logger.get_security_events(limit)
    return events

@router.get("/export")
async def export_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    logger: AuditLogger = Depends(get_audit_logger)
):
    """Export audit logs as JSON"""
    export_data = await logger.export_logs(start_date, end_date)
    return {"data": export_data}
