"""
Prompt Injection Detection Service
"""
import logging
import re
import base64
import unicodedata
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PromptInjectionDetector:
    """Detect prompt injection and jailbreak attempts"""
    
    def __init__(self):
        # Homoglyph mappings (common lookalikes used in attacks)
        self.homoglyph_map = {
            # Cyrillic lookalikes
            'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
            'і': 'i', 'ј': 'j', 'ѕ': 's', 'һ': 'h', 'ԁ': 'd', 'ԍ': 'g',
            # Greek lookalikes
            'α': 'a', 'β': 'b', 'ε': 'e', 'ι': 'i', 'ο': 'o', 'ρ': 'p', 'τ': 't', 'υ': 'y',
            # Other Unicode tricks
            'ı': 'i', 'ℓ': 'l', '𝐢': 'i', '𝐠': 'g', '𝐧': 'n', '𝐨': 'o', '𝐫': 'r', '𝐞': 'e',
        }
        
        # Injection patterns
        self.injection_patterns = [
            r"ignore (all )?previous (instructions|rules|prompts|commands)",
            r"you are now (a different|no longer|not)",
            r"forget (everything|all instructions|your role|previous)",
            r"new (instructions|rules|system prompt|role|task)",
            r"disregard (all )?previous",
            r"act as (if you are|a different|though you)",
            r"pretend (you are|to be|that you)",
            r"roleplay as",
            r"system:\s*\n",
            r"<\|im_start\|>",  # Chat template injection
            r"<\|im_end\|>",
            r"###\s*instruction",
            r"override (your|the) (instructions|rules|settings)",
            r"bypass (your|the) (restrictions|limitations|rules)",
            r"you must (now|ignore|forget)",
        ]
        
        # Jailbreak keywords
        self.jailbreak_keywords = [
            "DAN", "do anything now", "jailbreak", 
            "unrestricted mode", "developer mode",
            "god mode", "sudo mode", "admin mode",
            "bypass restrictions", "remove limitations",
            "ignore ethics", "ignore safety"
        ]
        
        # Encoded content patterns
        self.encoded_patterns = [
            r'[A-Za-z0-9+/]{40,}={0,2}',  # Base64
            r'\\x[0-9a-fA-F]{2}',  # Hex encoding
            r'&#\d{2,4};',  # HTML entities
            r'%[0-9a-fA-F]{2}',  # URL encoding
        ]
        
        # Role manipulation patterns
        self.role_manipulation = [
            r"you are (not|no longer) (an|a) (assistant|AI|chatbot)",
            r"your (new|real) (role|purpose|task) is",
            r"from now on,? you (will|must|should|are)",
        ]
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text to detect obfuscated injection attempts
        
        Handles:
        - Unicode normalization (NFKC)
        - Homoglyph replacement (Cyrillic/Greek lookalikes)
        - Zero-width character removal
        - Excessive whitespace normalization
        - Case normalization
        """
        # Step 1: Unicode normalization (NFKC - compatibility decomposition + canonical composition)
        # Converts fullwidth/halfwidth chars, ligatures, etc. to standard forms
        normalized = unicodedata.normalize('NFKC', text)
        
        # Step 2: Remove zero-width and invisible characters
        # These are often used to hide injection patterns
        zero_width_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # Zero-width no-break space (BOM)
            '\u2060',  # Word joiner
            '\u180e',  # Mongolian vowel separator
        ]
        for char in zero_width_chars:
            normalized = normalized.replace(char, '')
        
        # Step 3: Replace homoglyphs (lookalike characters)
        # Attackers use Cyrillic/Greek chars that look like Latin
        for homoglyph, replacement in self.homoglyph_map.items():
            normalized = normalized.replace(homoglyph, replacement)
        
        # Step 4: Normalize whitespace
        # Replace multiple spaces/tabs/newlines with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Step 5: Remove control characters (except newline/tab)
        normalized = ''.join(
            char for char in normalized 
            if unicodedata.category(char)[0] != 'C' or char in '\n\t '
        )
        
        # Step 6: Normalize case for detection (preserve original for logging)
        normalized = normalized.strip()
        
        return normalized
    
    async def detect_injection(self, query: str) -> Dict[str, Any]:
        """
        Detect prompt injection attempts with normalization
        """
        # Normalize query to detect obfuscated attacks
        normalized_query = self._normalize_text(query)
        query_lower = normalized_query.lower()
        
        # Check for injection patterns
        injection_found = []
        for pattern in self.injection_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                injection_found.append({
                    "pattern": pattern,
                    "matches": matches
                })
        
        # Check for jailbreak keywords
        jailbreak_found = [
            kw for kw in self.jailbreak_keywords 
            if kw.lower() in query_lower
        ]
        
        # Check for role manipulation
        role_manipulation_found = []
        for pattern in self.role_manipulation:
            if re.search(pattern, query_lower):
                role_manipulation_found.append(pattern)
        
        # Check for encoded content
        encoded_result = await self._check_encoded_content(query)
        
        # Calculate risk score
        risk_score = (
            len(injection_found) * 0.25 + 
            len(jailbreak_found) * 0.3 +
            len(role_manipulation_found) * 0.25 +
            (0.3 if encoded_result['suspicious'] else 0)
        )
        
        risk_level = "low"
        action = "ALLOW"
        
        if risk_score > 0.7:
            risk_level = "high"
            action = "BLOCK"
        elif risk_score > 0.3:
            risk_level = "medium"
            action = "WARN"
        
        result = {
            "risk_level": risk_level,
            "risk_score": min(risk_score, 1.0),
            "action": action,
            "injection_patterns": injection_found,
            "jailbreak_keywords": jailbreak_found,
            "role_manipulation": role_manipulation_found,
            "encoded_content": encoded_result,
            "recommendation": self._get_recommendation(risk_level, action)
        }
        
        if risk_level != "low":
            logger.warning(
                f"Prompt injection detected - Level: {risk_level}, "
                f"Score: {risk_score:.2f}, Action: {action}"
            )
        
        return result
    
    async def _check_encoded_content(self, query: str) -> Dict[str, Any]:
        """Check for encoded content that might hide injection attempts"""
        
        encoded_found = []
        decoded_content = []
        suspicious = False
        
        # Check for base64
        base64_matches = re.findall(self.encoded_patterns[0], query)
        for match in base64_matches:
            try:
                decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                decoded_content.append(decoded)
                
                # Check if decoded content contains injection patterns
                if any(
                    re.search(pattern, decoded.lower()) 
                    for pattern in self.injection_patterns
                ):
                    suspicious = True
                    encoded_found.append({
                        "type": "base64",
                        "encoded": match[:50] + "...",
                        "decoded": decoded[:100] + "...",
                        "suspicious": True
                    })
            except Exception:
                pass
        
        return {
            "encoded_found": len(encoded_found) > 0,
            "encoded_items": encoded_found,
            "suspicious": suspicious
        }
    
    def _get_recommendation(self, risk_level: str, action: str) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            "high": "BLOCK this request. High-confidence prompt injection detected. Do not process.",
            "medium": "WARN user. Possible injection attempt. Process with extra caution and sanitization.",
            "low": "ALLOW request. No injection detected."
        }
        return recommendations.get(risk_level, "ALLOW request.")
    
    def get_safe_rejection_message(self) -> str:
        """Get safe rejection message for blocked requests"""
        return (
            "I cannot process this request as it appears to contain instructions "
            "that could compromise my function. Please rephrase your question "
            "in a straightforward manner."
        )
    
    async def sanitize_query(self, query: str) -> str:
        """
        Sanitize query by normalizing and removing suspicious patterns
        """
        # First normalize to handle obfuscation
        sanitized = self._normalize_text(query)
        
        # Remove system prompt markers
        sanitized = re.sub(r'system:\s*\n', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<\|im_start\|>', '', sanitized)
        sanitized = re.sub(r'<\|im_end\|>', '', sanitized)
        
        # Remove instruction markers
        sanitized = re.sub(r'###\s*instruction', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
