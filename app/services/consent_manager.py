"""
Consent Manager Service
Manages user consent for data usage (GDPR compliance)
Uses in-memory storage instead of database
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ConsentManager:
    """Manage user consent for GDPR compliance"""
    
    def __init__(self):
        # In-memory storage
        self.consents = {}
        
    async def record_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        purpose: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """Record user consent"""
        if user_id not in self.consents:
            self.consents[user_id] = []
        
        consent_record = {
            "id": len(self.consents[user_id]) + 1,
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "purpose": purpose,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow(),
            "revoked": False
        }
        
        self.consents[user_id].append(consent_record)
        
        logger.info(f"Consent recorded: {consent_type} for user {user_id} - {granted}")
        return consent_record
    
    async def check_consent(
        self,
        user_id: str,
        consent_type: str
    ) -> bool:
        """Check if user has granted consent"""
        if user_id not in self.consents:
            return False
        
        user_consents = self.consents[user_id]
        
        # Get most recent consent of this type
        relevant_consents = [
            c for c in user_consents
            if c['consent_type'] == consent_type and not c['revoked']
        ]
        
        if not relevant_consents:
            return False
        
        latest_consent = max(relevant_consents, key=lambda x: x['timestamp'])
        return latest_consent['granted']
    
    async def revoke_consent(
        self,
        user_id: str,
        consent_type: str
    ) -> bool:
        """Revoke user consent"""
        if user_id not in self.consents:
            return False
        
        revoked_any = False
        for consent in self.consents[user_id]:
            if consent['consent_type'] == consent_type and not consent['revoked']:
                consent['revoked'] = True
                consent['revoked_at'] = datetime.utcnow()
                revoked_any = True
        
        if revoked_any:
            logger.info(f"Consent revoked: {consent_type} for user {user_id}")
        
        return revoked_any
    
    async def get_user_consents(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all consents for a user"""
        if user_id not in self.consents:
            return []
        
        return sorted(
            self.consents[user_id],
            key=lambda x: x['timestamp'],
            reverse=True
        )
    
    async def get_active_consents(
        self,
        user_id: str
    ) -> Dict[str, bool]:
        """Get active consent status for all types"""
        if user_id not in self.consents:
            return {}
        
        consent_types = set(c['consent_type'] for c in self.consents[user_id])
        
        active_consents = {}
        for consent_type in consent_types:
            active_consents[consent_type] = await self.check_consent(user_id, consent_type)
        
        return active_consents
    
    async def export_user_consents(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Export user consent data (GDPR right to access)"""
        consents = await self.get_user_consents(user_id)
        
        return {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "consents": [
                {
                    "consent_type": c['consent_type'],
                    "granted": c['granted'],
                    "purpose": c['purpose'],
                    "timestamp": c['timestamp'].isoformat(),
                    "revoked": c['revoked']
                }
                for c in consents
            ]
        }
