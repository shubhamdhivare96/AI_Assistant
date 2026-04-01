"""
PII Masking Service using Presidio
"""
import logging
from typing import Dict, List, Any, Optional
import hashlib
import re

logger = logging.getLogger(__name__)

# Try to import Presidio, fallback to regex-based if not available
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("Presidio not available, using regex-based PII masking")

class PIIMasker:
    """
    PII Masking Service
    Masks personally identifiable information in text
    """
    
    def __init__(self):
        if PRESIDIO_AVAILABLE:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self.use_presidio = True
        else:
            self.use_presidio = False
        
        # Regex patterns for fallback
        self.patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "name": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'  # Simple name pattern
        }
    
    async def mask_pii(
        self, 
        text: str, 
        strategy: str = "hash"
    ) -> Dict[str, Any]:
        """
        Mask PII in text using specified strategy
        
        Args:
            text: Input text
            strategy: "replace", "redact", or "hash"
        
        Returns:
            Dict with original, masked text, and entities found
        """
        try:
            if self.use_presidio:
                return await self._mask_with_presidio(text, strategy)
            else:
                return await self._mask_with_regex(text, strategy)
                
        except Exception as e:
            logger.error(f"Error masking PII: {str(e)}")
            return {
                "original": text,
                "masked": text,
                "entities_found": 0,
                "error": str(e)
            }
    
    async def _mask_with_presidio(
        self, 
        text: str, 
        strategy: str
    ) -> Dict[str, Any]:
        """Mask PII using Presidio"""
        # Analyze text for PII
        results = self.analyzer.analyze(
            text=text,
            entities=[
                "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                "CREDIT_CARD", "US_SSN", "LOCATION",
                "DATE_TIME", "IP_ADDRESS", "URL"
            ],
            language="en"
        )
        
        # Apply masking strategy
        if strategy == "replace":
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig(
                        "replace",
                        {"new_value": "{entity_type}_{index}"}
                    )
                }
            )
        elif strategy == "redact":
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={"DEFAULT": OperatorConfig("redact")}
            )
        elif strategy == "hash":
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={"DEFAULT": OperatorConfig("hash")}
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return {
            "original": text,
            "masked": anonymized.text,
            "entities_found": len(results),
            "entities": [
                {
                    "type": r.entity_type,
                    "score": r.score,
                    "start": r.start,
                    "end": r.end
                }
                for r in results
            ],
            "strategy": strategy
        }
    
    async def _mask_with_regex(
        self, 
        text: str, 
        strategy: str
    ) -> Dict[str, Any]:
        """Fallback: Mask PII using regex patterns"""
        masked_text = text
        entities_found = []
        
        for entity_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                original = match.group()
                
                if strategy == "replace":
                    replacement = f"[{entity_type.upper()}]"
                elif strategy == "redact":
                    replacement = "[REDACTED]"
                elif strategy == "hash":
                    replacement = self._hash_value(original)
                else:
                    replacement = original
                
                masked_text = masked_text.replace(original, replacement)
                entities_found.append({
                    "type": entity_type,
                    "original": original,
                    "replacement": replacement
                })
        
        return {
            "original": text,
            "masked": masked_text,
            "entities_found": len(entities_found),
            "entities": entities_found,
            "strategy": strategy,
            "method": "regex_fallback"
        }
    
    def _hash_value(self, value: str) -> str:
        """Hash a value for consistent masking"""
        return hashlib.md5(value.encode()).hexdigest()[:8]
    
    async def mask_student_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask PII in student data dictionary
        
        Args:
            data: Dict with student data
        
        Returns:
            Dict with masked data
        """
        masked_data = data.copy()
        
        # Mask text fields
        text_fields = ["query", "message", "content", "name", "comment"]
        for field in text_fields:
            if field in masked_data and isinstance(masked_data[field], str):
                result = await self.mask_pii(masked_data[field], strategy="hash")
                masked_data[field] = result['masked']
        
        # Mask nested metadata
        if "metadata" in masked_data and isinstance(masked_data["metadata"], dict):
            for key, value in masked_data["metadata"].items():
                if isinstance(value, str):
                    result = await self.mask_pii(value, strategy="hash")
                    masked_data["metadata"][key] = result['masked']
        
        return masked_data
    
    def is_available(self) -> bool:
        """Check if Presidio is available"""
        return self.use_presidio
