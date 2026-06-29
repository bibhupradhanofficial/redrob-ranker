import sys
import os

# Add parent directory to sys.path to allow imports from ranker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ranker.data_loader import DataLoader
from ranker.skills_scorer import SkillsScorer
from ranker.career_scorer import CareerScorer
from ranker.experience_scorer import ExperienceScorer
from ranker.location_scorer import LocationScorer
from ranker.education_scorer import EducationScorer

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_scorers.py <path_to_candidates_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' does not exist.")
        sys.exit(1)

    print(f"Initializing DataLoader with: {filepath}")
    loader = DataLoader(filepath)
    candidates = loader.load_all(max_candidates=10)
    print(f"Loaded {len(candidates)} candidates for testing.\n")

    # Instantiate scorers
    skills_scorer = SkillsScorer()
    career_scorer = CareerScorer()
    experience_scorer = ExperienceScorer()
    location_scorer = LocationScorer()
    education_scorer = EducationScorer()

    # Table header
    print("=" * 125)
    print(f"{'ID':<15} | {'Title':<30} | {'Skills':<10} | {'Career':<10} | {'Experience':<10} | {'Location':<10} | {'Education':<10}")
    print("-" * 125)

    errors = 0

    for c in candidates:
        candidate_id = c.get("candidate_id") or c.get("id") or "N/A"
        profile = c.get("profile") or {}
        title = profile.get("current_title") or c.get("current_title") or "N/A"
        if len(title) > 28:
            title = title[:25] + "..."

        # Calculate scores
        s_score = skills_scorer.score(c)
        c_score = career_scorer.score(c)
        x_score = experience_scorer.score(c)
        l_score = location_scorer.score(c)
        e_score = education_scorer.score(c)

        # Print row
        print(f"{candidate_id:<15} | {title:<30} | {s_score:<10.4f} | {c_score:<10.4f} | {x_score:<10.4f} | {l_score:<10.4f} | {e_score:<10.4f}")

        # Check bounds
        for name, score in [
            ("Skills", s_score),
            ("Career", c_score),
            ("Experience", x_score),
            ("Location", l_score),
            ("Education", e_score)
        ]:
            if not (0.0 <= score <= 1.0):
                print(f"ERROR: {candidate_id} has out-of-bounds {name} score: {score}")
                errors += 1

    print("=" * 125)
    if errors > 0:
        print(f"Verification FAILED with {errors} score out-of-bound errors.")
        sys.exit(1)
    else:
        print("Verification PASSED! All scores are floats within the [0.0, 1.0] range.")

if __name__ == "__main__":
    main()
