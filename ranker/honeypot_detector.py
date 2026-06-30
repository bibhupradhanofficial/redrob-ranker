import logging
import datetime
from dateutil import parser

logger = logging.getLogger(__name__)

class HoneypotDetector:
    """
    Detects candidates with impossible or inconsistent profiles.
    ~80 honeypot candidates exist in the 100K pool.
    Honeypots are forced to relevance tier 0 in ground truth.
    If >10% of top-100 are honeypots -> disqualification.

    Returns True if the candidate is a suspected honeypot.
    A honeypot candidate should receive a score_multiplier of 0.01
    (not filtered entirely — just ranked near bottom, because they DO exist in the pool).
    """

    CURRENT_YEAR = 2026

    def _fast_parse_date(self, date_str: str) -> datetime.datetime:
        if not date_str:
            return datetime.datetime.now()
        s = str(date_str).strip()
        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            try:
                return datetime.datetime(int(s[:4]), int(s[5:7]), int(s[8:10]))
            except ValueError:
                pass
        elif len(s) >= 7 and s[4] == '-':
            try:
                return datetime.datetime(int(s[:4]), int(s[5:7]), 1)
            except ValueError:
                pass
        elif len(s) == 4 and s.isdigit():
            try:
                return datetime.datetime(int(s), 1, 1)
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
                    end_date = datetime.datetime.now()
                
                delta = end_date - start_date
                total_days += max(0, delta.days)
            except Exception:
                pass
                
        if total_days > 0:
            return round(total_days / 365.25, 1)
        return 0.0

    def get_flags(self, candidate: dict) -> list[str]:
        flags = []
        
        # Parse and safely extract YOE
        profile = candidate.get("profile") or {}
        yoe = profile.get("years_of_experience")
        if yoe is None:
            yoe = candidate.get("years_of_experience")
        if yoe is None:
            yoe_val = self._compute_yoe_from_history(candidate)
        else:
            try:
                yoe_val = float(yoe)
            except (ValueError, TypeError):
                yoe_val = 0.0

        history = candidate.get("career_history") or []

        # 1. EXPERIENCE TIMELINE INCONSISTENCY & EDUCATION CHRONOLOGY
        education = candidate.get("education") or []
        end_years = []
        start_years = []
        bach_end = None
        mast_end = None
        phd_end = None

        for edu in education:
            if isinstance(edu, dict):
                ey = edu.get("end_year") or edu.get("endYear")
                sy = edu.get("start_year") or edu.get("startYear")
                deg = str(edu.get("degree") or "").lower().replace(".", "").strip()
                
                if ey is not None:
                    try:
                        ey_val = int(float(ey))
                        end_years.append(ey_val)
                        
                        # Match degrees to check academic chronology contradictions
                        if any(kw in deg for kw in ["btech", "be", "bs", "bsc", "bachelor"]):
                            bach_end = ey_val if bach_end is None else min(bach_end, ey_val)
                        elif any(kw in deg for kw in ["mtech", "ms", "me", "msc", "mba", "master"]):
                            mast_end = ey_val if mast_end is None else min(mast_end, ey_val)
                        elif any(kw in deg for kw in ["phd", "doctorate", "doctor"]):
                            phd_end = ey_val if phd_end is None else min(phd_end, ey_val)
                    except (ValueError, TypeError):
                        pass
                if sy is not None:
                    try:
                        start_years.append(int(float(sy)))
                    except (ValueError, TypeError):
                        pass
        
        # Check education chronology contradictions
        edu_contradiction = False
        if bach_end and mast_end and mast_end < bach_end:
            edu_contradiction = True
        if bach_end and phd_end and phd_end < bach_end:
            edu_contradiction = True
        if mast_end and phd_end and phd_end < mast_end:
            edu_contradiction = True

        if edu_contradiction:
            flags.append("EDUCATION_CHRONOLOGY_CONTRADICTION")

        # Compute threshold limit year for career start
        if start_years:
            limit_year = min(start_years)
        elif end_years:
            limit_year = min(end_years) - 4
        else:
            limit_year = self.CURRENT_YEAR - yoe_val - 4

        timeline_inconsistent = False
        for entry in history:
            if isinstance(entry, dict):
                title = str(entry.get("title") or entry.get("job_title") or "").lower()
                # Skip timeline checks for internships / student work / co-op / fellowships
                is_intern = any(kw in title for kw in ["intern", "co-op", "trainee", "student", "fellow"])
                if is_intern:
                    continue

                start_str = entry.get("start_date") or entry.get("startDate")
                if start_str:
                    try:
                        start_year = self._fast_parse_date(str(start_str)).year
                        if start_year < limit_year:
                            timeline_inconsistent = True
                            break
                    except Exception:
                        pass
        if timeline_inconsistent:
            flags.append("EXPERIENCE_TIMELINE_INCONSISTENCY")

        # 2. COMPANY EXISTENCE INCONSISTENCY
        company_inconsistent = False
        for entry in history:
            if isinstance(entry, dict):
                start_str = entry.get("start_date") or entry.get("startDate")
                dur = entry.get("duration_months")
                if start_str and dur is not None:
                    try:
                        start_year = self._fast_parse_date(str(start_str)).year
                        dur_val = float(dur)
                        max_allowed_months = 12 * (self.CURRENT_YEAR - start_year + 1)
                        if dur_val > max_allowed_months:
                            company_inconsistent = True
                            break
                    except Exception:
                        pass
        if company_inconsistent:
            flags.append("COMPANY_EXISTENCE_INCONSISTENCY")

        # 3. SKILL EXPERT INFLATION
        skills = candidate.get("skills") or []
        expert_inflated_count = 0
        if isinstance(skills, list):
            for s in skills:
                if isinstance(s, dict):
                    prof = str(s.get("proficiency") or "").lower().strip()
                    try:
                        ends = int(float(s.get("endorsements") or 0))
                    except (ValueError, TypeError):
                        ends = 0
                    try:
                        dur = float(s.get("duration_months") or 0.0)
                    except (ValueError, TypeError):
                        dur = 0.0
                    
                    if prof == "expert" and ends == 0 and dur == 0.0:
                        expert_inflated_count += 1
        if expert_inflated_count > 5:
            flags.append("SKILL_EXPERT_INFLATION")

        # 4. EXPERIENCE OVERFLOW
        total_months = 0.0
        for entry in history:
            if isinstance(entry, dict):
                dur = entry.get("duration_months")
                if dur is not None:
                    try:
                        total_months += float(dur)
                    except (ValueError, TypeError):
                        pass
        if total_months > (yoe_val * 12) + 36:
            flags.append("EXPERIENCE_OVERFLOW")

        # 5. RESPONSE RATE IMPOSSIBLE VALUE
        signals = candidate.get("redrob_signals") or {}
        
        rr = signals.get("recruiter_response_rate")
        if rr is None:
            rr = candidate.get("recruiter_response_rate")
        
        icr = signals.get("interview_completion_rate")
        if icr is None:
            icr = candidate.get("interview_completion_rate")
            
        oar = signals.get("offer_acceptance_rate")
        if oar is None:
            oar = candidate.get("offer_acceptance_rate")

        impossible_value = False
        if rr is not None:
            try:
                rr_val = float(rr)
                if rr_val < 0.0 or rr_val > 1.0:
                    impossible_value = True
            except (ValueError, TypeError):
                pass
        if icr is not None:
            try:
                icr_val = float(icr)
                if icr_val < -1.0 or icr_val > 1.0:
                    impossible_value = True
            except (ValueError, TypeError):
                pass
        if oar is not None:
            try:
                oar_val = float(oar)
                if oar_val < -1.0 or oar_val > 1.0:
                    impossible_value = True
            except (ValueError, TypeError):
                pass
                
        if impossible_value:
            flags.append("RESPONSE_RATE_IMPOSSIBLE_VALUE")

        # 6. ASSESSMENT SCORE WITHOUT SKILL
        candidate_skill_names = set()
        if isinstance(skills, list):
            for s in skills:
                if isinstance(s, dict):
                    name = s.get("name") or s.get("skill_name") or ""
                else:
                    name = str(s)
                if name:
                    candidate_skill_names.add(name.lower().strip())
        elif isinstance(skills, str) and skills:
            for s in skills.split(","):
                candidate_skill_names.add(s.strip().lower())

        assessment_scores = signals.get("skill_assessment_scores") or {}
        orphaned_count = 0
        if isinstance(assessment_scores, dict):
            for skill_key in assessment_scores.keys():
                skill_key_clean = str(skill_key).lower().strip()
                if skill_key_clean not in candidate_skill_names:
                    orphaned_count += 1
                    
        if orphaned_count > 8:
            flags.append("ASSESSMENT_SCORE_WITHOUT_SKILL")

        return flags

    def is_honeypot(self, candidate: dict) -> bool:
        return len(self.get_flags(candidate)) > 0

    def honeypot_multiplier(self, candidate: dict) -> float:
        return 0.01 if self.is_honeypot(candidate) else 1.0
