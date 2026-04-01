"""
Consent Management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.services.consent_manager import ConsentManager

router = APIRouter(prefix="/consent", tags=["consent"])

# Pydantic models
class ConsentRequest(BaseModel):
    user_id: str
    consent_type: str
    granted: bool
    purpose: str
    metadata: Dict[str, Any] = {}

class ConsentResponse(BaseModel):
    id: int
    user_id: str
    consent_type: str
    granted: bool
    purpose: str
    timestamp: datetime
    revoked: bool

# Dependency
def get_consent_manager() -> ConsentManager:
    return ConsentManager()

@router.post("/", response_model=ConsentResponse)
async def record_consent(
    request: ConsentRequest,
    manager: ConsentManager = Depends(get_consent_manager)
):
    """Record user consent"""
    consent = await manager.record_consent(
        user_id=request.user_id,
        consent_type=request.consent_type,
        granted=request.granted,
        purpose=request.purpose,
        metadata=request.metadata
    )
    return consent

@router.get("/{user_id}", response_model=List[ConsentResponse])
async def get_user_consents(
    user_id: str,
    manager: ConsentManager = Depends(get_consent_manager)
):
    """Get all consents for a user"""
    consents = await manager.get_user_consents(user_id)
    return consents

@router.get("/{user_id}/active", response_model=Dict[str, bool])
async def get_active_consents(
    user_id: str,
    manager: ConsentManager = Depends(get_consent_manager)
):
    """Get active consent status for all types"""
    active_consents = await manager.get_active_consents(user_id)
    return active_consents

@router.post("/{user_id}/revoke/{consent_type}")
async def revoke_consent(
    user_id: str,
    consent_type: str,
    manager: ConsentManager = Depends(get_consent_manager)
):
    """Revoke user consent"""
    success = await manager.revoke_consent(user_id, consent_type)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found"
        )
    return {"message": "Consent revoked successfully"}

@router.get("/{user_id}/export")
async def export_user_consents(
    user_id: str,
    manager: ConsentManager = Depends(get_consent_manager)
):
    """Export user consent data (GDPR right to access)"""
    export_data = await manager.export_user_consents(user_id)
    return export_data
