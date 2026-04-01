"""
Anomaly Detection Service
Detects unusual usage patterns and potential abuse
Uses in-memory storage instead of database
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detect anomalies in system usage"""
    
    def __init__(self):
        # In-memory storage
        self.user_activity = defaultdict(lambda: {
            'requests': [],
            'tokens': [],
            'costs': [],
            'alerts': []
        })
        
        # Thresholds
        self.spike_threshold_sigma = 3.0
        self.rapid_fire_threshold = 10  # requests per minute
        self.cost_spike_threshold = 100.0  # dollars
        
    async def analyze_request(
        self,
        user_id: str,
        tokens_used: int,
        cost: float,
        request_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a request for anomalies"""
        activity = self.user_activity[user_id]
        now = datetime.utcnow()
        
        # Add to history
        activity['requests'].append({
            'timestamp': now,
            'tokens': tokens_used,
            'cost': cost,
            'metadata': request_metadata
        })
        activity['tokens'].append(tokens_used)
        activity['costs'].append(cost)
        
        # Keep only last 1000 entries
        if len(activity['requests']) > 1000:
            activity['requests'] = activity['requests'][-1000:]
            activity['tokens'] = activity['tokens'][-1000:]
            activity['costs'] = activity['costs'][-1000:]
        
        # Detect anomalies
        anomalies = []
        
        # 1. Rapid-fire detection
        recent_requests = [
            r for r in activity['requests']
            if (now - r['timestamp']).total_seconds() < 60
        ]
        if len(recent_requests) > self.rapid_fire_threshold:
            anomalies.append('rapid_fire')
        
        # 2. Token spike detection
        if len(activity['tokens']) > 10:
            mean_tokens = np.mean(activity['tokens'])
            std_tokens = np.std(activity['tokens'])
            if std_tokens > 0:
                z_score = (tokens_used - mean_tokens) / std_tokens
                if abs(z_score) > self.spike_threshold_sigma:
                    anomalies.append('token_spike')
        
        # 3. Cost spike detection
        if cost > self.cost_spike_threshold:
            anomalies.append('cost_spike')
        
        # 4. Unusual time pattern
        hour = now.hour
        if hour < 2 or hour > 23:  # Late night activity
            if len(recent_requests) > 5:
                anomalies.append('unusual_time')
        
        # Determine action
        is_anomaly = len(anomalies) > 0
        action = 'allow'
        message = 'Normal activity'
        
        if is_anomaly:
            # Log alert
            alert = {
                'timestamp': now,
                'anomaly_types': anomalies,
                'tokens': tokens_used,
                'cost': cost
            }
            activity['alerts'].append(alert)
            
            # Determine severity
            if 'cost_spike' in anomalies or len(anomalies) >= 2:
                action = 'block'
                message = f"Suspicious activity detected: {', '.join(anomalies)}"
            else:
                action = 'warn'
                message = f"Unusual activity detected: {', '.join(anomalies)}"
            
            logger.warning(f"Anomaly detected for user {user_id}: {anomalies}")
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_types': anomalies,
            'action': action,
            'message': message,
            'confidence': len(anomalies) / 4.0  # 4 types of anomalies
        }
    
    async def get_user_alerts(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get alerts for a user"""
        activity = self.user_activity[user_id]
        return sorted(
            activity['alerts'],
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    async def get_all_alerts(
        self,
        time_period: timedelta = timedelta(days=7),
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all recent alerts"""
        cutoff_time = datetime.utcnow() - time_period
        
        all_alerts = []
        for user_id, activity in self.user_activity.items():
            for alert in activity['alerts']:
                if alert['timestamp'] >= cutoff_time:
                    all_alerts.append({
                        'user_id': user_id,
                        **alert
                    })
        
        return sorted(
            all_alerts,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    async def get_anomaly_stats(
        self,
        time_period: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """Get anomaly statistics"""
        cutoff_time = datetime.utcnow() - time_period
        
        total_alerts = 0
        anomaly_types = defaultdict(int)
        
        for activity in self.user_activity.values():
            for alert in activity['alerts']:
                if alert['timestamp'] >= cutoff_time:
                    total_alerts += 1
                    for anomaly_type in alert['anomaly_types']:
                        anomaly_types[anomaly_type] += 1
        
        return {
            'total_alerts': total_alerts,
            'anomaly_breakdown': dict(anomaly_types),
            'time_period': str(time_period)
        }
