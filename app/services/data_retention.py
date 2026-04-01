"""
Data Retention Service
Manages data retention policies for GDPR compliance
Uses in-memory storage instead of database
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class DataRetentionService:
    """Manage data retention and cleanup"""
    
    def __init__(self):
        # In-memory storage
        self.retention_policies = {
            'conversations': timedelta(days=90),
            'audit_logs': timedelta(days=365),
            'feedback': timedelta(days=180),
            'errors': timedelta(days=30),
            'soft_deleted': timedelta(days=7)
        }
        
        self.deleted_items = []
        
    async def cleanup_old_data(
        self,
        data_store: Dict,
        data_type: str
    ) -> Dict[str, Any]:
        """Clean up old data based on retention policy"""
        if data_type not in self.retention_policies:
            logger.warning(f"No retention policy for {data_type}")
            return {"deleted": 0, "error": "No retention policy"}
        
        retention_period = self.retention_policies[data_type]
        cutoff_date = datetime.utcnow() - retention_period
        
        deleted_count = 0
        
        # Handle different data structures
        if isinstance(data_store, list):
            original_count = len(data_store)
            data_store[:] = [
                item for item in data_store
                if item.get('timestamp', datetime.utcnow()) >= cutoff_date
            ]
            deleted_count = original_count - len(data_store)
        
        elif isinstance(data_store, dict):
            keys_to_delete = []
            for key, value in data_store.items():
                if isinstance(value, dict) and 'timestamp' in value:
                    if value['timestamp'] < cutoff_date:
                        keys_to_delete.append(key)
                elif isinstance(value, list):
                    # Handle nested lists
                    original_count = len(value)
                    value[:] = [
                        item for item in value
                        if item.get('timestamp', datetime.utcnow()) >= cutoff_date
                    ]
                    deleted_count += original_count - len(value)
            
            for key in keys_to_delete:
                del data_store[key]
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old {data_type} records")
        
        return {
            "data_type": data_type,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_period_days": retention_period.days
        }
    
    async def soft_delete(
        self,
        item: Dict,
        data_type: str
    ) -> Dict[str, Any]:
        """Soft delete an item (mark for deletion)"""
        deleted_item = {
            "original_item": item,
            "data_type": data_type,
            "deleted_at": datetime.utcnow(),
            "permanent_deletion_date": datetime.utcnow() + self.retention_policies['soft_deleted']
        }
        
        self.deleted_items.append(deleted_item)
        
        logger.info(f"Soft deleted {data_type} item")
        return deleted_item
    
    async def restore_soft_deleted(
        self,
        item_id: str
    ) -> bool:
        """Restore a soft-deleted item"""
        for i, item in enumerate(self.deleted_items):
            if item['original_item'].get('id') == item_id:
                self.deleted_items.pop(i)
                logger.info(f"Restored soft-deleted item {item_id}")
                return True
        
        return False
    
    async def cleanup_soft_deleted(self) -> Dict[str, Any]:
        """Permanently delete soft-deleted items past retention period"""
        now = datetime.utcnow()
        
        original_count = len(self.deleted_items)
        self.deleted_items[:] = [
            item for item in self.deleted_items
            if item['permanent_deletion_date'] > now
        ]
        
        deleted_count = original_count - len(self.deleted_items)
        
        logger.info(f"Permanently deleted {deleted_count} soft-deleted items")
        
        return {
            "permanently_deleted": deleted_count,
            "remaining_soft_deleted": len(self.deleted_items)
        }
    
    async def get_retention_policy(
        self,
        data_type: str
    ) -> Dict[str, Any]:
        """Get retention policy for a data type"""
        if data_type not in self.retention_policies:
            return {"error": "No retention policy found"}
        
        return {
            "data_type": data_type,
            "retention_period_days": self.retention_policies[data_type].days
        }
    
    async def update_retention_policy(
        self,
        data_type: str,
        retention_days: int
    ) -> Dict[str, Any]:
        """Update retention policy"""
        self.retention_policies[data_type] = timedelta(days=retention_days)
        
        logger.info(f"Updated retention policy for {data_type}: {retention_days} days")
        
        return {
            "data_type": data_type,
            "retention_period_days": retention_days
        }
    
    async def get_all_policies(self) -> Dict[str, int]:
        """Get all retention policies"""
        return {
            data_type: period.days
            for data_type, period in self.retention_policies.items()
        }
