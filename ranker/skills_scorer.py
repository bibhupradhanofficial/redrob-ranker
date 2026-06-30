import logging
import re
from typing import Dict, Any, List
from ranker.jd_config import JD_REQUIRED_SKILLS, JD_NICE_TO_HAVE_SKILLS

logger = logging.getLogger(__name__)

class SkillsScorer:
    """
    Scores a candidate on skills fit against the JD.
    """

    PROFICIENCY_MULTIPLIERS = {
        "beginner": 0.5,
        "intermediate": 0.75,
        "advanced": 0.9,
        "expert": 1.0
    }

    def __init__(self):
        # Pre-normalize JD skills list once at initialization
        self.req_skills_normalized = []
        for kw in JD_REQUIRED_SKILLS:
            kw_norm = re.sub(r'[^a-z0-9]', ' ', kw.lower()).strip()
            if kw_norm:
                self.req_skills_normalized.append((kw_norm, kw_norm.split()))

        self.nice_skills_normalized = []
        for kw in JD_NICE_TO_HAVE_SKILLS:
            kw_norm = re.sub(r'[^a-z0-9]', ' ', kw.lower()).strip()
            if kw_norm:
                self.nice_skills_normalized.append((kw_norm, kw_norm.split()))

    def _match_skill(self, skill_name: str, normalized_skills_list: List[tuple]) -> bool:
        s_norm = re.sub(r'[^a-z0-9]', ' ', skill_name.lower()).strip()
        if not s_norm:
            return False
            
        s_words = s_norm.split()
        s_words_set = set(s_words)
        s_words_singular = {w[:-1] if w.endswith('s') and len(w) > 2 else w for w in s_words}
        
        for kw_norm, kw_words in normalized_skills_list:
            # Direct exact match
            if kw_norm == s_norm:
                return True
                
            if len(kw_words) == 1:
                kw_word = kw_words[0]
                kw_word_sing = kw_word[:-1] if kw_word.endswith('s') and len(kw_word) > 2 else kw_word
                if kw_word in s_words_set or kw_word_sing in s_words_singular:
                    return True
            else:
                # Multi-word keyword phrase
                if kw_norm in s_norm:
                    return True
                    
            if len(s_words) == 1:
                s_word = s_words[0]
                s_word_sing = s_word[:-1] if s_word.endswith('s') and len(s_word) > 2 else s_word
                if s_word in kw_words or s_word_sing in [w[:-1] if w.endswith('s') and len(w) > 2 else w for w in kw_words]:
                    return True
                    
        return False

    def score(self, candidate: dict) -> float:
        skills = candidate.get("skills") or []
        if not isinstance(skills, list):
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            else:
                skills = []

        redrob_signals = candidate.get("redrob_signals") or {}
        assessment_scores = redrob_signals.get("skill_assessment_scores") or {}

        total_weighted_score = 0.0
        
        # We target a sum of 6.0 as the denominator for normalization before penalty
        target_score = 6.0

        for skill in skills:
            skill_name = ""
            proficiency = "intermediate"
            endorsements = 0
            duration_months = 24.0  # Default to 2 years

            if isinstance(skill, dict):
                skill_name = skill.get("name") or skill.get("skill_name") or ""
                proficiency = skill.get("proficiency") or "intermediate"
                endorsements = skill.get("endorsements") or 0
                duration_months = skill.get("duration_months") or 24.0
            else:
                skill_name = str(skill)

            if not skill_name:
                continue

            # 1. Check match and base contribution
            is_req = self._match_skill(skill_name, self.req_skills_normalized)
            is_nice = self._match_skill(skill_name, self.nice_skills_normalized)

            if not is_req and not is_nice:
                continue

            base_contrib = 1.0 if is_req else 0.5

            # 2. Proficiency multiplier
            prof_lower = str(proficiency).lower()
            prof_mult = self.PROFICIENCY_MULTIPLIERS.get(prof_lower, 0.75)

            # 3. Endorsement trust multiplier
            try:
                ends = float(endorsements)
            except (ValueError, TypeError):
                ends = 0.0
            endorsement_mult = min(1.0, 0.7 + (ends / 100.0))

            # 4. Duration multiplier
            try:
                dur = float(duration_months)
            except (ValueError, TypeError):
                dur = 24.0
            duration_mult = min(1.0, dur / 24.0)

            # Calculate skill base score
            skill_score = base_contrib * prof_mult * endorsement_mult * duration_mult

            # 5. Assessment bonus
            # If skill name matches key in assessment_scores
            assessment_score = None
            for key, score_val in assessment_scores.items():
                if key.lower() == skill_name.lower() or key.lower() in skill_name.lower() or skill_name.lower() in key.lower():
                    try:
                        assessment_score = float(score_val)
                        break
                    except (ValueError, TypeError):
                        pass

            if assessment_score is not None:
                # Add small bonus, cap it at 0.2 max per skill
                assessment_bonus = min(0.2, assessment_score / 500.0)
                skill_score += assessment_bonus

            total_weighted_score += skill_score

        # Normalize the raw score
        normalized_score = min(1.0, total_weighted_score / target_score)

        # 6. KEYWORD STUFFER TRAP PENALTY
        # If candidate has more than 25 skills listed, penalize them
        if len(skills) > 25:
            penalty = max(0.7, 1.0 - (len(skills) - 25) * 0.01)
            normalized_score *= penalty

        return round(normalized_score, 4)
