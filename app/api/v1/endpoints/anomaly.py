"""
Anomaly Detection endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.services.anomaly_detector import AnomalyDetector

router = APIRouter(prefix="/anomaly", tags=["anomaly"])

# Pydantic models
class AnomalyAlert(BaseModel):
    user_id: str
    timestamp: datetime
    anomaly_types: List[str]
    tokens: int
    cost: float

class AnomalyStats(BaseModel):
    total_alerts: int
    anomaly_breakdown: dict
    time_period: str

# Dependency to get anomaly detector
def get_anomaly_detector() -> AnomalyDetector:
    return AnomalyDetector()

@router.get("/alerts", response_model=List[AnomalyAlert])
async def get_all_alerts(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    detector: AnomalyDetector = Depends(get_anomaly_detector)
):
    """Get all recent anomaly alerts"""
    time_period = timedelta(days=days)
    alerts = await detector.get_all_alerts(time_period, limit)
    return alerts

@router.get("/alerts/{user_id}", response_model=List[AnomalyAlert])
async def get_user_alerts(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    detector: AnomalyDetector = Depends(get_anomaly_detector)
):
    """Get anomaly alerts for a specific user"""
    alerts = await detector.get_user_alerts(user_id, limit)
    return alerts

@router.get("/stats", response_model=AnomalyStats)
async def get_anomaly_stats(
    days: int = Query(7, ge=1, le=365),
    detector: AnomalyDetector = Depends(get_anomaly_detector)
):
    """Get anomaly detection statistics"""
    time_period = timedelta(days=days)
    stats = await detector.get_anomaly_stats(time_period)
    return stats
