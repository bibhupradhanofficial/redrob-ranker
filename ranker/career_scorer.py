import logging
from typing import List, Dict, Any
from dateutil import parser
from datetime import datetime
from ranker.jd_config import JD_DISQUALIFYING_SIGNALS

logger = logging.getLogger(__name__)

class CareerScorer:
    """
    Scores the career trajectory — title relevance, company type, career progression.
    """

    TARGET_TITLES = [
        "AI Engineer", "ML Engineer", "Data Scientist", "Research Engineer",
        "Software Engineer", "Backend Engineer", "ML Researcher", "Applied Scientist"
    ]

    PRODUCT_INDUSTRIES = [
        "Software", "AI/ML", "SaaS", "E-commerce", "Fintech", "Edtech", 
        "HealthTech", "Product", "Technology", "Internet", "B2B Software"
    ]

    SENIORITY_KEYWORDS = {
        "director": 5,
        "head": 5,
        "principal": 4,
        "staff": 4,
        "architect": 4,
        "lead": 3,
        "senior": 2,
        "sr": 2,
        "associate": 1,
        "junior": 0,
        "jr": 0,
        "intern": -1
    }

    def _match_title(self, title: str, targets: List[str]) -> bool:
        if not title:
            return False
        title_lower = title.lower()
        return any(t.lower() in title_lower or title_lower in t.lower() for t in targets)

    def _is_consulting(self, company_name: str, consulting_list: List[str]) -> bool:
        if not company_name:
            return False
        co_lower = company_name.lower()
        return any(c.lower() in co_lower for c in consulting_list)

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

    def _get_entry_months(self, entry: dict) -> float:
        if "duration_months" in entry and entry["duration_months"] is not None:
            try:
                return float(entry["duration_months"])
            except (ValueError, TypeError):
                pass
        # Fallback to date parsing
        start_str = entry.get("start_date") or entry.get("startDate")
        end_str = entry.get("end_date") or entry.get("endDate")
        if not start_str:
            return 0.0
        try:
            start_date = self._fast_parse_date(str(start_str))
            if end_str:
                end_date = self._fast_parse_date(str(end_str))
            else:
                end_date = datetime.now()
            return max(0.0, (end_date - start_date).days / 30.4375)
        except Exception:
            return 0.0

    def _get_title_seniority(self, title: str) -> int:
        t_lower = title.lower()
        max_val = 1  # Default level for normal mid-level
        for kw, val in self.SENIORITY_KEYWORDS.items():
            if kw in t_lower:
                max_val = max(max_val, val)
        return max_val

    def score(self, candidate: dict) -> float:
        profile = candidate.get("profile") or {}
        redrob_signals = candidate.get("redrob_signals") or {}
        career_history = candidate.get("career_history") or []

        # 1. TITLE SCORE
        current_title = (
            profile.get("current_title")
            or candidate.get("current_title")
            or profile.get("title")
            or candidate.get("title")
            or ""
        )
        
        current_title_score = 1.0 if self._match_title(current_title, self.TARGET_TITLES) else 0.0

        history_match_scores = []
        for entry in career_history:
            if isinstance(entry, dict):
                hist_title = entry.get("title") or entry.get("job_title") or entry.get("jobTitle") or ""
                if hist_title:
                    score_val = 1.0 if self._match_title(hist_title, self.TARGET_TITLES) else 0.0
                    history_match_scores.append(score_val)

        best_history_title_score = max(history_match_scores) if history_match_scores else 0.0
        
        title_score = max(current_title_score, 0.8 * best_history_title_score)

        # Disqualifying titles check
        disqualifiers = JD_DISQUALIFYING_SIGNALS.get("non_ai_titles") or []
        if self._match_title(current_title, disqualifiers):
            title_score *= 0.15

        # Pure research / academic check
        research_kws = JD_DISQUALIFYING_SIGNALS.get("pure_research_keywords") or []
        if self._match_title(current_title, research_kws):
            # Only downweight if they don't have a strong applied title like ML Engineer or AI Engineer or Backend Engineer
            applied_titles = ["ai engineer", "ml engineer", "software engineer", "backend engineer", "applied scientist"]
            if not any(at in current_title.lower() for at in applied_titles):
                title_score *= 0.60

        # 2. COMPANY TYPE SCORE
        consulting_list = JD_DISQUALIFYING_SIGNALS.get("consulting_companies") or []
        consulting_months = 0.0
        total_career_months = 0.0

        for entry in career_history:
            if isinstance(entry, dict):
                months = self._get_entry_months(entry)
                total_career_months += months
                company_name = entry.get("company") or entry.get("company_name") or ""
                if self._is_consulting(company_name, consulting_list):
                    consulting_months += months

        consulting_fraction = consulting_months / max(1.0, total_career_months)
        company_score = 1.0 - (0.7 * consulting_fraction)

        # Check if current company is a consulting firm
        current_co = profile.get("current_company") or candidate.get("current_company") or ""
        if not current_co and career_history:
            # Fallback: check first entry in career_history
            first_entry = career_history[0]
            if isinstance(first_entry, dict):
                current_co = first_entry.get("company") or first_entry.get("company_name") or ""
        
        if current_co and self._is_consulting(current_co, consulting_list):
            company_score *= 0.85

        # 3. CAREER PROGRESSION SCORE
        career_prog_score = 0.0
        if career_history:
            # Filter and parse career history
            valid_entries = []
            for entry in career_history:
                if not isinstance(entry, dict):
                    continue
                start_str = entry.get("start_date") or entry.get("startDate")
                title_val = entry.get("title") or entry.get("job_title") or ""
                comp_val = entry.get("company") or entry.get("company_name") or ""
                if start_str:
                    try:
                        start_date = self._fast_parse_date(str(start_str))
                        valid_entries.append((start_date, title_val, comp_val, entry))
                    except Exception:
                        pass
            
            # Sort chronologically by start date
            valid_entries.sort(key=lambda x: x[0])

            if valid_entries:
                # Chronological roles list
                chronological_titles = [x[1] for x in valid_entries]
                chronological_companies = [x[2] for x in valid_entries]

                # Base progression score
                career_prog_score = 0.05
                
                # Check if latest title is senior
                latest_title = chronological_titles[-1]
                latest_seniority = self._get_title_seniority(latest_title)
                if latest_seniority >= 2:
                    career_prog_score += 0.05

                # Check for upward trajectory (later role's seniority > earlier role's seniority)
                has_upward = False
                for i in range(len(chronological_titles)):
                    for j in range(i + 1, len(chronological_titles)):
                        if self._get_title_seniority(chronological_titles[j]) > self._get_title_seniority(chronological_titles[i]):
                            has_upward = True
                            break
                    if has_upward:
                        break

                if has_upward:
                    career_prog_score += 0.05

                # Stagnation check: only 1 company for >= 10 years (120 months)
                unique_companies = {co.lower().strip() for co in chronological_companies if co}
                if len(unique_companies) == 1 and total_career_months >= 120.0:
                    career_prog_score = 0.0

        # 4. PRODUCT COMPANY BONUS
        product_bonus = 0.0
        for entry in career_history:
            if isinstance(entry, dict):
                industry = entry.get("industry") or entry.get("company_industry") or ""
                # Check if industry matches product industries (substring match)
                is_prod = False
                if industry:
                    ind_lower = str(industry).lower()
                    if any(p.lower() in ind_lower for p in self.PRODUCT_INDUSTRIES):
                        is_prod = True
                if is_prod:
                    product_bonus += 0.1

        product_bonus = min(0.3, product_bonus)

        # 5. OPEN SOURCE & LINKEDIN BONUS
        os_bonus = 0.0
        try:
            github_activity = float(redrob_signals.get("github_activity_score") or 0.0)
        except (ValueError, TypeError):
            github_activity = 0.0

        if github_activity > 50.0:
            os_bonus += 0.05

        if redrob_signals.get("linkedin_connected") is True:
            os_bonus += 0.02

        # Final score formula
        raw = (0.45 * title_score) + (0.30 * company_score) + (0.15 * career_prog_score) + product_bonus + os_bonus
        return round(min(1.0, raw), 4)
