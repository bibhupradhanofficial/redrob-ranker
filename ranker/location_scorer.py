import logging
from ranker.jd_config import JD_PREFERRED_LOCATIONS

logger = logging.getLogger(__name__)

class LocationScorer:
    """
    Scores location fit for Pune/Noida role (hybrid, India-preferred).
    """

    TIER_1_CITIES = ["pune", "noida", "delhi", "ncr", "gurugram", "gurgaon"]
    TIER_2_CITIES = ["hyderabad", "mumbai", "bangalore", "bengaluru", "chennai"]

    def score(self, candidate: dict) -> float:
        profile = candidate.get("profile") or {}
        redrob_signals = candidate.get("redrob_signals") or {}

        # 1. Extract and normalize country
        country = profile.get("country") or candidate.get("country") or ""
        
        # 2. Extract and normalize city/location
        location_val = profile.get("location") or candidate.get("location") or ""
        city = ""
        if isinstance(location_val, dict):
            city = location_val.get("city") or location_val.get("state") or ""
            if not country:
                country = location_val.get("country") or ""
        else:
            city = str(location_val)

        city_clean = city.strip().lower()
        country_clean = country.strip().lower()

        # Fallback: if country is empty but city matches preferred Indian cities, assume India
        if not country_clean and city_clean:
            if any(p.lower() in city_clean for p in JD_PREFERRED_LOCATIONS):
                country_clean = "india"

        # 3. Extract and normalize relocation preference
        willing_to_relocate = redrob_signals.get("willing_to_relocate")
        if willing_to_relocate is None:
            willing_to_relocate = candidate.get("willing_to_relocate")
        willing_to_relocate = bool(willing_to_relocate)

        # 4. Scoring logic
        if country_clean != "india":
            # Outside India
            if willing_to_relocate:
                score = 0.40
            else:
                score = 0.30
        else:
            # Inside India
            is_tier_1 = any(t in city_clean for t in self.TIER_1_CITIES)
            is_tier_2 = any(t in city_clean for t in self.TIER_2_CITIES)

            if is_tier_1:
                score = 1.0
            elif is_tier_2:
                score = 0.85
            else:
                score = 0.65

            # Add relocation bonus if applicable
            if willing_to_relocate:
                score = min(1.0, score + 0.10)

        return round(score, 4)
