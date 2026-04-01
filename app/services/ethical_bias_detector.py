"""
Ethical Bias Detection Service
"""
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EthicalBiasDetector:
    """Detect ethical bias and stereotypes in content"""
    
    def __init__(self):
        self.demographic_keywords = {
            "gender": ["male", "female", "man", "woman", "boy", "girl", "he", "she", "his", "her"],
            "culture": ["indian", "western", "eastern", "hindu", "muslim", "christian", "buddhist", "sikh"],
            "socioeconomic": ["rich", "poor", "wealthy", "urban", "rural", "privileged", "underprivileged"],
            "caste": ["brahmin", "dalit", "scheduled", "tribe", "obc", "general"],
            "region": ["north", "south", "east", "west", "metro", "village", "city"]
        }
        
        self.stereotype_patterns = [
            r"girls are (not )?good at",
            r"boys (always|never|can't|cannot)",
            r"(rich|poor) students (can't|cannot|always|never)",
            r"(urban|rural) students (can't|cannot|always)",
            r"(brahmin|dalit|obc) students",
            r"only (boys|girls|men|women) can",
            r"(boys|girls) should (not )?",
        ]
        
        self.inclusive_language_violations = [
            r"\bhe\b(?! or she)",  # Using "he" without "he or she"
            r"\bhim\b(?! or her)",
            r"\bhis\b(?! or her)",
            r"\bmanpower\b",  # Should be "workforce"
            r"\bchairman\b",  # Should be "chairperson"
            r"\bfreshman\b",  # Should be "first-year student"
        ]
    
    async def detect_bias(
        self, 
        response: str, 
        retrieved_docs: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Detect demographic bias and stereotypes
        """
        # Check for demographic representation
        representation = self._check_representation(response)
        
        # Check for stereotype patterns
        stereotypes = self._check_stereotypes(response)
        
        # Check for inclusive language violations
        language_issues = self._check_inclusive_language(response)
        
        # Check for diversity in examples (if docs provided)
        diversity_score = 1.0
        if retrieved_docs:
            diversity_score = self._check_diversity(retrieved_docs)
        
        # Calculate overall bias score
        bias_score = (
            representation['bias_score'] * 0.4 + 
            stereotypes['bias_score'] * 0.4 + 
            language_issues['bias_score'] * 0.2
        )
        
        # Adjust for diversity
        bias_score = bias_score * (1 - diversity_score * 0.2)
        
        bias_level = "low" if bias_score < 0.3 else "medium" if bias_score < 0.7 else "high"
        
        result = {
            "bias_level": bias_level,
            "bias_score": round(bias_score, 3),
            "representation": representation,
            "stereotypes": stereotypes,
            "language_issues": language_issues,
            "diversity_score": round(diversity_score, 3),
            "recommendation": self._generate_recommendation(bias_score, stereotypes, language_issues)
        }
        
        if bias_level != "low":
            logger.warning(f"Bias detected - Level: {bias_level}, Score: {bias_score:.3f}")
        
        return result
    
    def _check_representation(self, text: str) -> Dict[str, Any]:
        """Check if demographic groups are represented equitably"""
        text_lower = text.lower()
        counts = {}
        
        for category, keywords in self.demographic_keywords.items():
            counts[category] = sum(text_lower.count(kw) for kw in keywords)
        
        # Calculate imbalance
        category_counts = [c for c in counts.values() if c > 0]
        if not category_counts:
            return {"counts": counts, "bias_score": 0.0, "imbalance": 0.0}
        
        max_count = max(category_counts)
        min_count = min(category_counts)
        imbalance = (max_count - min_count) / max_count if max_count > 0 else 0
        
        # Check for gender-specific language imbalance
        gender_imbalance = 0.0
        if counts.get("gender", 0) > 0:
            male_terms = sum(text_lower.count(kw) for kw in ["male", "man", "boy", "he", "his"])
            female_terms = sum(text_lower.count(kw) for kw in ["female", "woman", "girl", "she", "her"])
            total_gender = male_terms + female_terms
            if total_gender > 0:
                gender_imbalance = abs(male_terms - female_terms) / total_gender
        
        bias_score = (imbalance + gender_imbalance) / 2
        
        return {
            "counts": counts,
            "bias_score": round(bias_score, 3),
            "imbalance": round(imbalance, 3),
            "gender_imbalance": round(gender_imbalance, 3)
        }
    
    def _check_stereotypes(self, text: str) -> Dict[str, Any]:
        """Check for stereotype patterns"""
        text_lower = text.lower()
        found_stereotypes = []
        
        for pattern in self.stereotype_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                # Find the full sentence containing the match
                sentences = text.split('.')
                for sentence in sentences:
                    if re.search(pattern, sentence.lower()):
                        found_stereotypes.append({
                            "pattern": pattern,
                            "sentence": sentence.strip(),
                            "severity": "high"
                        })
        
        bias_score = min(len(found_stereotypes) * 0.3, 1.0)
        
        return {
            "found": found_stereotypes,
            "count": len(found_stereotypes),
            "bias_score": round(bias_score, 3)
        }
    
    def _check_inclusive_language(self, text: str) -> Dict[str, Any]:
        """Check for inclusive language violations"""
        violations = []
        
        for pattern in self.inclusive_language_violations:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append({
                    "term": match.group(),
                    "position": match.start(),
                    "suggestion": self._get_inclusive_alternative(match.group())
                })
        
        bias_score = min(len(violations) * 0.2, 1.0)
        
        return {
            "violations": violations,
            "count": len(violations),
            "bias_score": round(bias_score, 3)
        }
    
    def _get_inclusive_alternative(self, term: str) -> str:
        """Get inclusive alternative for a term"""
        alternatives = {
            "manpower": "workforce",
            "chairman": "chairperson",
            "freshman": "first-year student",
            "he": "they or he/she",
            "him": "them or him/her",
            "his": "their or his/her"
        }
        return alternatives.get(term.lower(), "use gender-neutral language")
    
    def _check_diversity(self, documents: List[Dict]) -> float:
        """Check for diversity in examples and sources"""
        if not documents:
            return 1.0
        
        # Check for diversity in document sources
        unique_sources = set()
        for doc in documents:
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'unknown')
            unique_sources.add(source)
        
        # More unique sources = higher diversity
        diversity_score = min(len(unique_sources) / 5, 1.0)  # Normalize to 5 sources
        
        return diversity_score
    
    def _generate_recommendation(
        self, 
        bias_score: float, 
        stereotypes: Dict, 
        language_issues: Dict
    ) -> str:
        """Generate recommendation for high-bias responses"""
        if bias_score > 0.7:
            recommendations = []
            
            if stereotypes['count'] > 0:
                recommendations.append("Remove stereotypical language")
            
            if language_issues['count'] > 0:
                recommendations.append("Use gender-neutral language")
            
            if not recommendations:
                recommendations.append("Review for demographic balance")
            
            return "High bias detected. " + ". ".join(recommendations) + "."
        
        elif bias_score > 0.3:
            return "Moderate bias detected. Consider more diverse examples and inclusive language."
        
        return ""
    
    async def suggest_improvements(self, text: str, bias_result: Dict) -> List[str]:
        """Suggest specific improvements to reduce bias"""
        suggestions = []
        
        # Suggestions for stereotypes
        if bias_result['stereotypes']['count'] > 0:
            for stereotype in bias_result['stereotypes']['found']:
                suggestions.append(
                    f"Remove stereotypical statement: '{stereotype['sentence']}'"
                )
        
        # Suggestions for language issues
        if bias_result['language_issues']['count'] > 0:
            for violation in bias_result['language_issues']['violations']:
                suggestions.append(
                    f"Replace '{violation['term']}' with '{violation['suggestion']}'"
                )
        
        # Suggestions for representation
        if bias_result['representation']['gender_imbalance'] > 0.5:
            suggestions.append(
                "Balance gender representation in examples"
            )
        
        return suggestions
