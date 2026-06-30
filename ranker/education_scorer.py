import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EducationScorer:
    """
    Scores education — degree level, field relevance, institution tier.
    """

    def _get_degree_score(self, degree: str) -> float:
        if not degree:
            return 0.4  # Default if degree string is empty but entry exists
        
        deg_lower = degree.lower().replace(".", "").strip()
        tokens = set(re.findall(r'\b\w+\b', deg_lower))
        
        # PhD / Doctorate
        if any(kw in tokens for kw in ["phd", "doctorate", "doctor"]) or "doctor of philosophy" in deg_lower:
            return 1.0
            
        # Master's
        if any(kw in tokens for kw in ["mtech", "ms", "me", "msc", "mba"]) or "master" in tokens or any(kw in deg_lower for kw in ["master of", "masters"]):
            return 0.9
            
        # Bachelor's
        if any(kw in tokens for kw in ["btech", "be", "bs", "bsc"]) or "bachelor" in tokens or any(kw in deg_lower for kw in ["bachelor of", "bachelors"]):
            return 0.75
            
        # Diploma / Associate
        if any(kw in tokens for kw in ["diploma", "associate"]):
            return 0.5
            
        # Default fallback for unknown degrees
        return 0.75

    def _get_field_multiplier(self, field: str) -> float:
        if not field:
            return 0.5  # Assume non-STEM if empty
            
        field_lower = field.lower().strip()
        
        # CS / AI / ECE / EEE
        cs_keywords = [
            "computer science", "cs", "artificial intelligence", "ai", 
            "machine learning", "ml", "data science", "information technology", 
            "it", "electronics", "ece", "eee", "computer engineering"
        ]
        if any(kw in field_lower for kw in cs_keywords):
            return 1.0
            
        # Stats / Math / Physics / Generic Engineering
        math_keywords = ["statistics", "stats", "mathematics", "math", "physics", "engineering"]
        if any(kw in field_lower for kw in math_keywords):
            return 0.85
            
        # Other STEM
        stem_keywords = ["science", "technology", "chemistry", "biology", "stem", "biotechnology", "mathematical"]
        if any(kw in field_lower for kw in stem_keywords):
            return 0.7
            
        # Non-STEM
        return 0.5

    def _get_tier_bonus(self, tier: str) -> float:
        if not tier:
            return 0.0
            
        tier_clean = str(tier).strip().lower()
        if tier_clean == "tier_1":
            return 0.15
        elif tier_clean == "tier_2":
            return 0.07
        return 0.0

    def score(self, candidate: dict) -> float:
        education = candidate.get("education") or []
        if not isinstance(education, list) or not education:
            return 0.4  # Default score if no education listed

        best_score = 0.0
        
        for entry in education:
            if not isinstance(entry, dict):
                continue
                
            degree = entry.get("degree") or ""
            field = entry.get("field_of_study") or entry.get("field") or ""
            tier = entry.get("tier") or ""

            degree_score = self._get_degree_score(degree)
            field_mult = self._get_field_multiplier(field)
            tier_bonus = self._get_tier_bonus(tier)

            final_entry_score = (degree_score * field_mult) + tier_bonus
            final_entry_score = min(1.0, final_entry_score)
            
            if final_entry_score > best_score:
                best_score = final_entry_score

        # If we went through all entries and didn't find any valid dictionary, return default 0.4
        if best_score == 0.0:
            return 0.4

        return round(best_score, 4)
