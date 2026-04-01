"""
Audit Logger Service
Logs all system actions for compliance and security
Uses in-memory storage instead of database
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class AuditLogger:
    """Log system actions for audit trail"""
    
    def __init__(self):
        # In-memory storage
        self.audit_logs = []
        
    async def log_action(
        self,
        action_type: str,
        user_id: Optional[str],
        resource_type: str,
        resource_id: Optional[str],
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log an action"""
        log_entry = {
            "id": len(self.audit_logs) + 1,
            "timestamp": datetime.utcnow(),
            "action_type": action_type,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        self.audit_logs.append(log_entry)
        
        logger.info(f"Audit log: {action_type} by {user_id} on {resource_type}")
        return log_entry
    
    async def get_logs(
        self,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filters"""
        filtered_logs = self.audit_logs
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log['user_id'] == user_id]
        
        if action_type:
            filtered_logs = [log for log in filtered_logs if log['action_type'] == action_type]
        
        if resource_type:
            filtered_logs = [log for log in filtered_logs if log['resource_type'] == resource_type]
        
        return sorted(
            filtered_logs,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    async def get_user_activity(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get activity for a specific user"""
        return await self.get_logs(user_id=user_id, limit=limit)
    
    async def get_security_events(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get security-related events"""
        security_actions = [
            'login', 'logout', 'failed_login', 
            'permission_denied', 'suspicious_activity'
        ]
        
        security_logs = [
            log for log in self.audit_logs
            if log['action_type'] in security_actions
        ]
        
        return sorted(
            security_logs,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    async def export_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Export logs as JSON"""
        filtered_logs = self.audit_logs
        
        if start_date:
            filtered_logs = [log for log in filtered_logs if log['timestamp'] >= start_date]
        
        if end_date:
            filtered_logs = [log for log in filtered_logs if log['timestamp'] <= end_date]
        
        # Convert datetime to string for JSON serialization
        export_data = []
        for log in filtered_logs:
            log_copy = log.copy()
            log_copy['timestamp'] = log_copy['timestamp'].isoformat()
            export_data.append(log_copy)
        
        return json.dumps(export_data, indent=2)
