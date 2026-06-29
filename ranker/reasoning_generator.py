import logging
from ranker.jd_config import JD_REQUIRED_SKILLS, JD_NICE_TO_HAVE_SKILLS, JD_DISQUALIFYING_SIGNALS

logger = logging.getLogger(__name__)

class ReasoningGenerator:
    """
    Generates grounded, specific, JD-connected 1-2 sentence reasonings for each
    candidate in the top-100. Reasoning references actual facts from the
    candidate's profile.
    """

    PRODUCT_INDUSTRIES = [
        "software", "ai/ml", "saas", "e-commerce", "fintech", "edtech", 
        "healthtech", "product", "technology", "internet", "b2b software"
    ]

    def _get_top_matching_skills(self, candidate: dict, n: int = 3) -> list[str]:
        skills = candidate.get("skills") or []
        if not isinstance(skills, list):
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            else:
                skills = []

        all_jd_skills = set(s.lower() for s in JD_REQUIRED_SKILLS + JD_NICE_TO_HAVE_SKILLS)
        matching_skills = []

        for s in skills:
            name = ""
            proficiency = "intermediate"
            duration = 0.0
            ends = 0

            if isinstance(s, dict):
                name = s.get("name") or s.get("skill_name") or ""
                proficiency = s.get("proficiency") or "intermediate"
                try:
                    duration = float(s.get("duration_months") or 0.0)
                except (ValueError, TypeError):
                    duration = 0.0
                try:
                    ends = int(s.get("endorsements") or 0)
                except (ValueError, TypeError):
                    ends = 0
            else:
                name = str(s)

            if not name:
                continue

            name_lower = name.lower().strip()
            # Substring/exact match against JD skills
            is_match = False
            for jd_s in all_jd_skills:
                if jd_s in name_lower or name_lower in jd_s:
                    is_match = True
                    break

            if is_match:
                # Calculate sorting weight: expert=4, advanced=3, intermediate=2, beginner=1
                prof_weight = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}.get(str(proficiency).lower(), 2)
                matching_skills.append({
                    "name": name,
                    "duration": duration,
                    "endorsements": ends,
                    "prof_weight": prof_weight
                })

        # Sort matching skills by prof_weight descending, then duration descending, then endorsements descending
        matching_skills.sort(key=lambda x: (-x["prof_weight"], -x["duration"], -x["endorsements"]))
        return [x["name"] for x in matching_skills[:n]]

    def _get_company_descriptor(self, candidate: dict) -> str:
        history = candidate.get("career_history") or []
        consulting_list = JD_DISQUALIFYING_SIGNALS.get("consulting_companies") or []

        consulting_months = 0.0
        product_months = 0.0
        total_months = 0.0

        for entry in history:
            if isinstance(entry, dict):
                try:
                    dur = float(entry.get("duration_months") or 0.0)
                except (ValueError, TypeError):
                    dur = 0.0
                total_months += dur

                co_name = str(entry.get("company") or entry.get("company_name") or "").lower()
                ind = str(entry.get("industry") or entry.get("company_industry") or "").lower()

                is_consulting = any(c.lower() in co_name for c in consulting_list)
                is_product = any(p in ind for p in self.PRODUCT_INDUSTRIES)

                if is_consulting:
                    consulting_months += dur
                elif is_product:
                    product_months += dur

        if total_months > 0:
            if consulting_months / total_months > 0.5:
                return "consulting-heavy background"
            if product_months / total_months > 0.4:
                return "product-focused engineering background"

        return "software industry background"

    def _get_location_phrase(self, candidate: dict) -> str:
        profile = candidate.get("profile") or {}
        country = str(profile.get("country") or candidate.get("country") or "").strip().lower()
        
        location_val = profile.get("location") or candidate.get("location") or ""
        city = ""
        if isinstance(location_val, dict):
            city = location_val.get("city") or location_val.get("state") or ""
            if not country:
                country = str(location_val.get("country") or "").strip().lower()
        else:
            city = str(location_val)

        city_clean = city.strip()
        
        # Fallback to check city names for country
        if not country and city_clean.lower() in [loc.lower() for loc in ["pune", "noida", "bangalore", "bengaluru", "hyderabad", "mumbai", "chennai", "delhi", "gurugram", "gurgaon"]]:
            country = "india"

        signals = candidate.get("redrob_signals") or {}
        willing_to_relocate = bool(signals.get("willing_to_relocate") or candidate.get("willing_to_relocate") or False)

        if country == "india":
            if city_clean:
                if city_clean.lower() in ["pune", "noida", "delhi", "ncr", "gurugram", "gurgaon"]:
                    return f"being based locally in {city_clean}"
                return f"being located in {city_clean} (willing to relocate)" if willing_to_relocate else f"being based in {city_clean}"
            return "being based in India"
        else:
            if city_clean:
                loc_name = f"{city_clean}, {country.title()}" if country else city_clean
                return f"residing in {loc_name} (open to relocation)" if willing_to_relocate else f"residing in {loc_name}"
            return f"residing in {country.title()}" if country else "being based remotely"

    def _get_notice_phrase(self, signals: dict) -> str:
        notice = signals.get("notice_period_days")
        if notice is None:
            return "immediate availability"
        try:
            n_days = int(float(notice))
            if n_days <= 0:
                return "immediate availability"
            return f"{n_days}-day notice period"
        except (ValueError, TypeError):
            return "standard notice period"

    def _get_experience_phrase(self, candidate: dict) -> str:
        profile = candidate.get("profile") or {}
        yoe = profile.get("years_of_experience")
        if yoe is None:
            yoe = candidate.get("years_of_experience")
        try:
            yoe_val = float(yoe) if yoe is not None else None
        except (ValueError, TypeError):
            yoe_val = None

        if yoe_val is not None:
            return f"{round(yoe_val, 1)} years of experience"
        return "a relevant professional experience tenure"

    def generate(self, candidate: dict, score_components: dict, rank: int) -> str:
        profile = candidate.get("profile") or {}
        signals = candidate.get("redrob_signals") or {}

        # Safely extract YOE val
        yoe = profile.get("years_of_experience") or candidate.get("years_of_experience")
        try:
            yoe_val = float(yoe) if yoe is not None else 0.0
        except (ValueError, TypeError):
            yoe_val = 0.0

        title = profile.get("current_title") or candidate.get("current_title") or "Software Engineer"
        
        # 1. STRONGEST SIGNAL (Step 1)
        skills_score = score_components.get("skills_score", 0.0)
        career_score = score_components.get("career_score", 0.0)
        tfidf_score = score_components.get("tfidf_score", 0.0)

        top_skills = self._get_top_matching_skills(candidate, n=3)
        company_descriptor = self._get_company_descriptor(candidate)

        if skills_score > 0.65 and top_skills:
            skills_str = ", ".join(top_skills)
            strongest_signal = f"Demonstrates strong technical capabilities in {skills_str}"
        elif career_score > 0.65:
            strongest_signal = f"Offers a robust professional background as a {title} with a {company_descriptor}"
        elif tfidf_score > 0.45:
            strongest_signal = f"Has a highly relevant engineering background matching the search criteria"
        else:
            strongest_signal = f"Presents a relevant background in software engineering and technical skills"

        # 2. SUPPORTING SIGNAL (Step 2)
        behavioral_multiplier = score_components.get("behavioral_multiplier", 1.0)
        location_score = score_components.get("location_score", 0.0)
        experience_score = score_components.get("experience_score", 0.0)
        
        location_phrase = self._get_location_phrase(candidate)
        exp_phrase = self._get_experience_phrase(candidate)

        if experience_score == 1.0:
            supporting_signal = f"their {exp_phrase} aligns perfectly with the target 5-9 year window"
        elif location_score > 0.8:
            supporting_signal = f"location fit is excellent, {location_phrase}"
        elif behavioral_multiplier > 1.0:
            supporting_signal = "they maintain high activity and responsiveness on the platform"
        else:
            supporting_signal = f"they possess {exp_phrase}"

        # 3. CONCERNS (Step 3)
        notice_days = signals.get("notice_period_days")
        try:
            notice_val = int(float(notice_days)) if notice_days is not None else 0
        except (ValueError, TypeError):
            notice_val = 0

        concern = None
        if notice_val > 90:
            concern = f"a long notice period of {notice_val} days may require negotiation"
        elif behavioral_multiplier < 0.6:
            concern = "limited recent platform activity indicates possible availability concerns"
        elif location_score < 0.6:
            concern = f"relocation is required due to {location_phrase}"
        elif career_score < 0.4:
            concern = "most of their career has been adjacent to core AI/ML systems engineering"
        elif experience_score < 0.7:
            if yoe_val < 4.0:
                concern = f"their experience level ({round(yoe_val, 1)} YOE) is slightly below the ideal founding requirements"
            elif yoe_val > 12.0:
                concern = f"their seniority level ({round(yoe_val, 1)} YOE) exceeds the core target range"

        # 4. ASSEMBLE REASONING (Step 4)
        # Ranks 1-15: No concerns, combine strongest + supporting.
        # Ranks 16-39: Include concern if critical, else combine strongest + supporting.
        # Ranks 40-100: Always append concern (or fallback concern if none triggered).
        if rank <= 15:
            reasoning = f"{strongest_signal}. Additionally, {supporting_signal}."
        elif rank <= 39:
            if concern:
                reasoning = f"{strongest_signal}. However, {concern}."
            else:
                reasoning = f"{strongest_signal}. Additionally, {supporting_signal}."
        else:
            if not concern:
                # Default concern if none triggered for lower ranks
                if yoe_val > 0:
                    concern = f"notice period and relocation readiness ({location_phrase}) will need to be confirmed"
                else:
                    concern = "further technical assessments are recommended to verify core competency"
            reasoning = f"{strongest_signal}. However, {concern}."

        # Final sanitization
        reasoning = reasoning.strip()
        if not reasoning.endswith("."):
            reasoning += "."
            
        # Ensure reasoning is within 250 characters
        if len(reasoning) > 250:
            reasoning = reasoning[:247] + "..."

        return reasoning
