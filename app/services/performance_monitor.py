"""
Performance Monitoring Service
NOTE: Prometheus is optional - system works without it
"""
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Prometheus is optional - only for production monitoring
try:
    from prometheus_client import Histogram, Counter, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Prometheus client not available - metrics will be logged only")

# SQLAlchemy removed
# from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for a request"""
    retrieval_latency: float
    generation_latency: float
    total_latency: float
    cache_hit: bool
    tokens_used: int
    hallucination_risk: str
    user_satisfaction: Optional[float] = None
    query_complexity: Optional[str] = None

class PerformanceMonitor:
    """Monitor and track system performance"""
    
    def __init__(self):
        # Prometheus metrics (optional)
        if PROMETHEUS_AVAILABLE:
            self.retrieval_latency = Histogram(
                'retrieval_latency_seconds',
                'Time spent on retrieval',
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
            )
            
            self.generation_latency = Histogram(
                'generation_latency_seconds',
                'Time spent on generation',
                buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
            )
            
            self.total_latency = Histogram(
                'total_latency_seconds',
                'Total request latency',
                buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
            )
            
            self.cache_hit_rate = Counter(
                'cache_hits_total',
                'Number of cache hits'
            )
            
            self.cache_miss_rate = Counter(
                'cache_misses_total',
                'Number of cache misses'
            )
            
            self.hallucination_detections = Counter(
                'hallucination_detections_total',
                'Number of hallucinations detected',
                ['risk_level']
            )
            
            self.user_satisfaction = Histogram(
                'user_satisfaction_score',
                'User satisfaction ratings',
                buckets=[1, 2, 3, 4, 5]
            )
            
            self.tokens_used = Counter(
                'tokens_used_total',
                'Total tokens used'
            )
            
            self.requests_total = Counter(
                'requests_total',
                'Total requests processed',
                ['status']
            )
        else:
            # Fallback: just log metrics
            logger.info("Performance monitoring in logging mode (Prometheus not available)")
        
        # In-memory storage for recent metrics
        self.recent_metrics: List[PerformanceMetrics] = []
        self.max_recent = 1000
    
    async def track_request(
        self, 
        query: str, 
        response: str, 
        metrics: PerformanceMetrics
    ):
        """
        Track performance metrics for a request
        """
        try:
            # Record to Prometheus if available
            if PROMETHEUS_AVAILABLE:
                # Record latencies
                self.retrieval_latency.observe(metrics.retrieval_latency)
                self.generation_latency.observe(metrics.generation_latency)
                self.total_latency.observe(metrics.total_latency)
                
                # Record cache performance
                if metrics.cache_hit:
                    self.cache_hit_rate.inc()
                else:
                    self.cache_miss_rate.inc()
                
                # Record hallucination detections
                if metrics.hallucination_risk != "low":
                    self.hallucination_detections.labels(
                        risk_level=metrics.hallucination_risk
                    ).inc()
                
                # Record user satisfaction (if provided)
                if metrics.user_satisfaction:
                    self.user_satisfaction.observe(metrics.user_satisfaction)
                
                # Record tokens used
                self.tokens_used.inc(metrics.tokens_used)
                
                # Record successful request
                self.requests_total.labels(status='success').inc()
            
            # Store in recent metrics (always)
            self.recent_metrics.append(metrics)
            if len(self.recent_metrics) > self.max_recent:
                self.recent_metrics.pop(0)
            
            # Log metrics (always)
            logger.info(
                f"Request tracked - Total: {metrics.total_latency:.2f}s, "
                f"Retrieval: {metrics.retrieval_latency:.2f}s, "
                f"Generation: {metrics.generation_latency:.2f}s, "
                f"Cache: {'HIT' if metrics.cache_hit else 'MISS'}, "
                f"Tokens: {metrics.tokens_used}"
            )
            
        except Exception as e:
            logger.error(f"Error tracking metrics: {str(e)}")
            if PROMETHEUS_AVAILABLE:
                self.requests_total.labels(status='error').inc()
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for dashboard
        """
        if not self.recent_metrics:
            return {
                "message": "No metrics available yet",
                "total_requests": 0
            }
        
        # Calculate averages from recent metrics
        total_requests = len(self.recent_metrics)
        
        avg_retrieval = sum(m.retrieval_latency for m in self.recent_metrics) / total_requests
        avg_generation = sum(m.generation_latency for m in self.recent_metrics) / total_requests
        avg_total = sum(m.total_latency for m in self.recent_metrics) / total_requests
        
        cache_hits = sum(1 for m in self.recent_metrics if m.cache_hit)
        cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        hallucinations = sum(
            1 for m in self.recent_metrics 
            if m.hallucination_risk in ['medium', 'high']
        )
        hallucination_rate = (hallucinations / total_requests * 100) if total_requests > 0 else 0
        
        satisfaction_scores = [
            m.user_satisfaction for m in self.recent_metrics 
            if m.user_satisfaction is not None
        ]
        avg_satisfaction = (
            sum(satisfaction_scores) / len(satisfaction_scores) 
            if satisfaction_scores else None
        )
        
        total_tokens = sum(m.tokens_used for m in self.recent_metrics)
        
        return {
            "total_requests": total_requests,
            "avg_retrieval_latency": round(avg_retrieval, 3),
            "avg_generation_latency": round(avg_generation, 3),
            "avg_total_latency": round(avg_total, 3),
            "cache_hit_rate": round(cache_hit_rate, 2),
            "hallucination_rate": round(hallucination_rate, 2),
            "avg_user_satisfaction": round(avg_satisfaction, 2) if avg_satisfaction else None,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_request": round(total_tokens / total_requests, 0) if total_requests > 0 else 0
        }
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Get latency percentiles"""
        if not self.recent_metrics:
            return {}
        
        latencies = sorted([m.total_latency for m in self.recent_metrics])
        n = len(latencies)
        
        return {
            "p50": latencies[int(n * 0.5)],
            "p90": latencies[int(n * 0.9)],
            "p95": latencies[int(n * 0.95)],
            "p99": latencies[int(n * 0.99)] if n > 100 else latencies[-1]
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """Check system health"""
        summary = await self.get_performance_summary()
        percentiles = self.get_latency_percentiles()
        
        # Define health thresholds
        is_healthy = True
        issues = []
        
        if summary.get("avg_total_latency", 0) > 3.0:
            is_healthy = False
            issues.append("High average latency (>3s)")
        
        if summary.get("cache_hit_rate", 0) < 30:
            issues.append("Low cache hit rate (<30%)")
        
        if summary.get("hallucination_rate", 0) > 10:
            is_healthy = False
            issues.append("High hallucination rate (>10%)")
        
        return {
            "healthy": is_healthy,
            "issues": issues,
            "summary": summary,
            "percentiles": percentiles,
            "timestamp": datetime.utcnow().isoformat()
        }

# Global monitor instance
performance_monitor = PerformanceMonitor()
