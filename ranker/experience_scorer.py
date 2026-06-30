import logging
from dateutil import parser
from datetime import datetime

logger = logging.getLogger(__name__)

class ExperienceScorer:
    """
    Scores years of experience against JD range of 5-9 years.
    """

    JD_IDEAL_MIN = 5.0
    JD_IDEAL_MAX = 9.0
    JD_SOFT_MIN = 4.0
    JD_SOFT_MAX = 10.0

    def _fast_parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now()
        s = str(date_str).strip()
        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            try:
                return datetime(int(s[:4]), int(s[5:7]), int(s[8:10]))
            except ValueError:
                pass
        elif len(s) >= 7 and s[4] == '-':
            try:
                return datetime(int(s[:4]), int(s[5:7]), 1)
            except ValueError:
                pass
        elif len(s) == 4 and s.isdigit():
            try:
                return datetime(int(s), 1, 1)
            except ValueError:
                pass
        return parser.parse(s)

    def _compute_yoe_from_history(self, candidate: dict) -> float:
        history = candidate.get("career_history") or []
        if not isinstance(history, list) or not history:
            return 0.0
            
        total_days = 0
        for entry in history:
            if not isinstance(entry, dict):
                continue
            start_str = entry.get("start_date") or entry.get("startDate")
            end_str = entry.get("end_date") or entry.get("endDate")
            
            if not start_str:
                continue
                
            try:
                start_date = self._fast_parse_date(str(start_str))
                if end_str:
                    end_date = self._fast_parse_date(str(end_str))
                else:
                    end_date = datetime.now()
                
                delta = end_date - start_date
                total_days += max(0, delta.days)
            except Exception:
                pass
                
        if total_days > 0:
            return round(total_days / 365.25, 1)
        return 0.0

    def score(self, candidate: dict) -> float:
        profile = candidate.get("profile") or {}
        yoe = profile.get("years_of_experience")
        
        # Check top-level as well
        if yoe is None:
            yoe = candidate.get("years_of_experience")
            
        # Fallback to history computation
        if yoe is None:
            yoe = self._compute_yoe_from_history(candidate)
            
        try:
            yoe = float(yoe)
        except (ValueError, TypeError):
            yoe = 0.0

        # Scoring Logic
        if self.JD_IDEAL_MIN <= yoe <= self.JD_IDEAL_MAX:
            score = 1.0
        elif self.JD_SOFT_MIN <= yoe < self.JD_IDEAL_MIN:
            # Linear interpolation from 0.75 to 1.0
            # At 4.0 -> 0.75, at 5.0 -> 1.0
            score = 0.75 + (yoe - self.JD_SOFT_MIN) * 0.25
        elif self.JD_IDEAL_MAX < yoe <= self.JD_SOFT_MAX:
            # Linear interpolation from 1.0 to 0.75
            # At 9.0 -> 1.0, at 10.0 -> 0.75
            score = 1.0 - (yoe - self.JD_IDEAL_MAX) * 0.25
        else:
            # Below 4 or above 10
            if yoe < self.JD_SOFT_MIN:
                distance = self.JD_SOFT_MIN - yoe
            else:
                distance = yoe - self.JD_SOFT_MAX
            
            score = max(0.0, 0.75 - distance * 0.1)

        # Exception: if years > 15, score caps at 0.55 (likely over-experienced / expensive)
        if yoe > 15.0:
            score = min(score, 0.55)

        return round(score, 4)
