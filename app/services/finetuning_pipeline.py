"""
Fine-tuning Pipeline
Collects data and prepares for model fine-tuning
Uses in-memory storage instead of database
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class FineTuningPipeline:
    """Manage fine-tuning data collection and preparation"""
    
    def __init__(self):
        # In-memory storage
        self.training_data = []
        self.feedback_data = []
        
    async def collect_training_example(
        self,
        query: str,
        response: str,
        feedback_score: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect a training example"""
        example = {
            'id': len(self.training_data) + 1,
            'query': query,
            'response': response,
            'feedback_score': feedback_score,
            'context': context,
            'timestamp': datetime.utcnow(),
            'used_in_training': False
        }
        
        self.training_data.append(example)
        
        logger.info(f"Collected training example with score {feedback_score}")
        return example
    
    async def get_low_satisfaction_queries(
        self,
        threshold: float = 3.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get queries with low satisfaction for improvement"""
        low_satisfaction = [
            ex for ex in self.training_data
            if ex['feedback_score'] < threshold
        ]
        
        return sorted(
            low_satisfaction,
            key=lambda x: x['feedback_score']
        )[:limit]
    
    async def get_high_quality_examples(
        self,
        threshold: float = 4.0,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get high-quality examples for fine-tuning"""
        high_quality = [
            ex for ex in self.training_data
            if ex['feedback_score'] >= threshold and not ex['used_in_training']
        ]
        
        return sorted(
            high_quality,
            key=lambda x: x['feedback_score'],
            reverse=True
        )[:limit]
    
    async def prepare_training_dataset(
        self,
        min_score: float = 4.0,
        max_examples: int = 1000
    ) -> Dict[str, Any]:
        """Prepare dataset for fine-tuning"""
        examples = await self.get_high_quality_examples(min_score, max_examples)
        
        # Format for fine-tuning
        formatted_data = []
        for ex in examples:
            formatted_data.append({
                'messages': [
                    {'role': 'user', 'content': ex['query']},
                    {'role': 'assistant', 'content': ex['response']}
                ]
            })
        
        # Mark as used
        for ex in examples:
            ex['used_in_training'] = True
        
        return {
            'dataset': formatted_data,
            'count': len(formatted_data),
            'min_score': min_score,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_training_stats(self) -> Dict[str, Any]:
        """Get training data statistics"""
        if not self.training_data:
            return {
                'total_examples': 0,
                'avg_score': 0,
                'high_quality_count': 0,
                'low_quality_count': 0
            }
        
        scores = [ex['feedback_score'] for ex in self.training_data]
        
        return {
            'total_examples': len(self.training_data),
            'avg_score': sum(scores) / len(scores),
            'high_quality_count': len([s for s in scores if s >= 4.0]),
            'low_quality_count': len([s for s in scores if s < 3.0]),
            'used_in_training': len([ex for ex in self.training_data if ex['used_in_training']])
        }
    
    async def analyze_improvement_areas(
        self,
        time_period: timedelta = timedelta(days=30)
    ) -> Dict[str, Any]:
        """Analyze areas needing improvement"""
        cutoff_time = datetime.utcnow() - time_period
        
        recent_low_quality = [
            ex for ex in self.training_data
            if ex['timestamp'] >= cutoff_time and ex['feedback_score'] < 3.0
        ]
        
        # Analyze common patterns in low-quality responses
        topics = defaultdict(int)
        for ex in recent_low_quality:
            # Simple topic extraction (could be improved with NLP)
            query_words = ex['query'].lower().split()
            for word in query_words:
                if len(word) > 4:  # Skip short words
                    topics[word] += 1
        
        top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'low_quality_count': len(recent_low_quality),
            'problematic_topics': [{'topic': t, 'count': c} for t, c in top_topics],
            'time_period': str(time_period)
        }
