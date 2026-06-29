import logging
import datetime
from dateutil import parser

logger = logging.getLogger(__name__)

class BehavioralScorer:
    """
    Scores the 23 Redrob behavioral signals. This acts as a MULTIPLIER on top of
    skill/career/experience scores — a perfect-on-paper candidate who has not logged
    in for 6 months or has a 5% recruiter response rate is not actually available
    and should be downweighted significantly.

    Returns a MULTIPLIER in [0.3, 1.2] rather than a raw [0, 1] score, because
    behavioral signals should boost or dampen profile scores, not replace them.
    """

    def score(self, candidate: dict) -> float:
        signals = candidate.get("redrob_signals") or {}

        # 1. AVAILABILITY SCORE (weight 0.35)
        open_to_work = signals.get("open_to_work_flag")
        if open_to_work is None:
            open_to_work = candidate.get("open_to_work_flag")
        if open_to_work is None:
            open_to_work = signals.get("open_to_work")
        if open_to_work is None:
            open_to_work = candidate.get("open_to_work")
        
        open_flag_score = 1.0 if bool(open_to_work) else 0.5

        # Recency score from last_active_date
        last_active = signals.get("last_active_date")
        recency_score = 0.15  # Default for dormant (180+ days or missing)
        if last_active:
            try:
                if isinstance(last_active, (datetime.datetime, datetime.date)):
                    last_active_date = last_active
                    if isinstance(last_active_date, datetime.datetime):
                        last_active_date = last_active_date.date()
                else:
                    last_active_date = parser.parse(str(last_active)).date()
                
                today = datetime.date.today()
                days_diff = (today - last_active_date).days
                if days_diff < 0:
                    days_diff = 0  # Safeguard for future dates

                if days_diff <= 14:
                    recency_score = 1.0
                elif days_diff <= 30:
                    recency_score = 0.9
                elif days_diff <= 60:
                    recency_score = 0.75
                elif days_diff <= 90:
                    recency_score = 0.55
                elif days_diff <= 180:
                    recency_score = 0.35
                else:
                    recency_score = 0.15
            except Exception as e:
                logger.warning(f"Error parsing last_active_date '{last_active}': {e}")
                recency_score = 0.15

        # Activity score
        apps_submitted = signals.get("applications_submitted_30d")
        if apps_submitted is None:
            apps_submitted = candidate.get("applications_submitted_30d")
        try:
            apps_submitted_val = float(apps_submitted) if apps_submitted is not None else 0.0
        except (ValueError, TypeError):
            apps_submitted_val = 0.0
        
        activity_score = min(1.0, apps_submitted_val / 5.0)

        availability = (0.4 * open_flag_score) + (0.4 * recency_score) + (0.2 * activity_score)

        # 2. RESPONSIVENESS SCORE (weight 0.30)
        recruiter_response = signals.get("recruiter_response_rate")
        if recruiter_response is None:
            recruiter_response = candidate.get("recruiter_response_rate")
        try:
            recruiter_response_rate = float(recruiter_response) if recruiter_response is not None else 0.0
        except (ValueError, TypeError):
            recruiter_response_rate = 0.0
        # Ensure rate is within [0, 1]
        recruiter_response_rate = max(0.0, min(1.0, recruiter_response_rate))

        response_time = signals.get("avg_response_time_hours")
        if response_time is None:
            response_time = candidate.get("avg_response_time_hours")
        response_time_score = 0.2  # Default for slow (>336h or missing)
        if response_time is not None:
            try:
                response_time_val = float(response_time)
                if response_time_val <= 24.0:
                    response_time_score = 1.0
                elif response_time_val <= 72.0:
                    response_time_score = 0.85
                elif response_time_val <= 168.0:
                    response_time_score = 0.65
                elif response_time_val <= 336.0:
                    response_time_score = 0.4
                else:
                    response_time_score = 0.2
            except (ValueError, TypeError):
                response_time_score = 0.2

        interview_completion = signals.get("interview_completion_rate")
        if interview_completion is None:
            interview_completion = candidate.get("interview_completion_rate")
        try:
            interview_completion_rate = float(interview_completion) if interview_completion is not None else 0.0
        except (ValueError, TypeError):
            interview_completion_rate = 0.0
        interview_completion_rate = max(0.0, min(1.0, interview_completion_rate))

        responsiveness = (0.45 * recruiter_response_rate) + \
                         (0.25 * response_time_score) + \
                         (0.30 * interview_completion_rate)

        # 3. ENGAGEMENT SCORE (weight 0.20)
        profile_completeness = signals.get("profile_completeness_score")
        if profile_completeness is None:
            profile_completeness = candidate.get("profile_completeness_score")
        try:
            profile_completeness_score = float(profile_completeness) if profile_completeness is not None else 0.0
        except (ValueError, TypeError):
            profile_completeness_score = 0.0
        profile_completeness_val = profile_completeness_score / 100.0

        verification_bonus = 0.0
        if signals.get("verified_email") is True:
            verification_bonus += 0.05
        if signals.get("verified_phone") is True:
            verification_bonus += 0.05
        if signals.get("linkedin_connected") is True:
            verification_bonus += 0.05

        saved_by_rec = signals.get("saved_by_recruiters_30d")
        try:
            saved_by_rec_val = float(saved_by_rec) if saved_by_rec is not None else 0.0
        except (ValueError, TypeError):
            saved_by_rec_val = 0.0
        saved_score = min(1.0, saved_by_rec_val / 10.0)

        engagement = (profile_completeness_val * 0.7) + verification_bonus + (saved_score * 0.3)

        # 4. NOTICE PERIOD PENALTY (applied as direct multiplier)
        notice_period = signals.get("notice_period_days")
        if notice_period is None:
            notice_period = candidate.get("notice_period_days")
        
        notice_period_days = 90  # Default to 90 days if missing
        if notice_period is not None:
            try:
                notice_period_days = int(float(notice_period))
            except (ValueError, TypeError):
                notice_period_days = 90

        if notice_period_days <= 0:
            notice_period_multiplier = 1.05
        elif notice_period_days <= 30:
            notice_period_multiplier = 1.0
        elif notice_period_days <= 60:
            notice_period_multiplier = 0.95
        elif notice_period_days <= 90:
            notice_period_multiplier = 0.88
        elif notice_period_days <= 120:
            notice_period_multiplier = 0.80
        else:
            notice_period_multiplier = 0.70

        # 5. OFFER ACCEPTANCE RATE (weight 0.15)
        offer_acceptance = signals.get("offer_acceptance_rate")
        if offer_acceptance is None:
            offer_acceptance = candidate.get("offer_acceptance_rate")
        
        try:
            offer_acceptance_val = float(offer_acceptance) if offer_acceptance is not None else -1.0
        except (ValueError, TypeError):
            offer_acceptance_val = -1.0

        if offer_acceptance_val == -1.0:
            offer_acceptance_score = 0.7
        else:
            offer_acceptance_score = max(0.0, min(1.0, offer_acceptance_val))

        # FINAL MULTIPLIER FORMULA
        base = (0.35 * availability) + (0.30 * responsiveness) + (0.20 * engagement) + (0.15 * offer_acceptance_score)
        multiplier = 0.3 + (base * 0.9)
        multiplier *= notice_period_multiplier

        return round(max(0.3, min(1.2, multiplier)), 4)
