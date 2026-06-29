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
from ranker.behavioral_scorer import BehavioralScorer
from ranker.honeypot_detector import HoneypotDetector
from ranker.composite_scorer import CompositeScorer

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

    # 1. Instantiate individual scorers for bound verification
    skills_scorer = SkillsScorer()
    career_scorer = CareerScorer()
    experience_scorer = ExperienceScorer()
    location_scorer = LocationScorer()
    education_scorer = EducationScorer()
    behavioral_scorer = BehavioralScorer()
    honeypot_detector = HoneypotDetector()

    # Table header
    print("=" * 165)
    print(f"{'ID':<15} | {'Title':<25} | {'Skills':<10} | {'Career':<10} | {'Experience':<10} | {'Location':<10} | {'Education':<10} | {'Behavioral':<10} | {'Honeypot':<10} | {'Flags':<25}")
    print("-" * 165)

    errors = 0

    for c in candidates:
        candidate_id = c.get("candidate_id") or c.get("id") or "N/A"
        profile = c.get("profile") or {}
        title = profile.get("current_title") or c.get("current_title") or "N/A"
        if len(title) > 23:
            title = title[:20] + "..."

        # Calculate scores
        s_score = skills_scorer.score(c)
        c_score = career_scorer.score(c)
        x_score = experience_scorer.score(c)
        l_score = location_scorer.score(c)
        e_score = education_scorer.score(c)
        b_score = behavioral_scorer.score(c)
        
        is_hp = honeypot_detector.is_honeypot(c)
        hp_mult = honeypot_detector.honeypot_multiplier(c)
        hp_flags = honeypot_detector.get_flags(c)
        flags_str = ",".join(hp_flags) if hp_flags else "None"

        # Print row
        print(f"{candidate_id:<15} | {title:<25} | {s_score:<10.4f} | {c_score:<10.4f} | {x_score:<10.4f} | {l_score:<10.4f} | {e_score:<10.4f} | {b_score:<10.4f} | {str(is_hp):<10} | {flags_str:<25}")

        # Check bounds for standard scorers
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

        # Check behavioral score bounds [0.3, 1.2]
        if not (0.3 <= b_score <= 1.2):
            print(f"ERROR: {candidate_id} has out-of-bounds Behavioral score: {b_score}")
            errors += 1

        # Check honeypot multiplier consistency
        expected_mult = 0.01 if is_hp else 1.0
        if hp_mult != expected_mult:
            print(f"ERROR: {candidate_id} honeypot multiplier {hp_mult} does not match expected {expected_mult}")
            errors += 1

    print("=" * 165)
    if errors > 0:
        print(f"Individual Scorer Verification FAILED with {errors} errors.\n")
        sys.exit(1)
    else:
        print("Individual Scorer Verification PASSED! All bounds and flags are valid.\n")

    # 2. Verify CompositeScorer and Pipeline
    print("Initializing CompositeScorer...")
    composite_scorer = CompositeScorer(use_semantic=True, semantic_top_n=5)
    
    # Run the ranking pipeline
    ranked_candidates = composite_scorer.score_all(candidates)
    
    print("\n" + "=" * 165)
    print("FINAL PIPELINE CANDIDATE RANKINGS (Normalized & Ranked)")
    print("=" * 165)
    print(f"{'Rank':<5} | {'ID':<15} | {'Composite Score':<18} | {'Raw Structural':<15} | {'TF-IDF':<10} | {'Semantic (Stage B)':<20} | {'Honeypot':<10}")
    print("-" * 165)
    
    for rank, r in enumerate(ranked_candidates, 1):
        cid = r["candidate_id"]
        comp = r["composite_score"]
        raw_struct = r["raw_structural"]
        tf = r["tfidf_score"]
        sem = r["semantic_score"]
        is_hp = r["is_honeypot"]
        
        sem_str = f"{sem:.4f}" if sem is not None else "Skipped"
        
        print(f"{rank:<5} | {cid:<15} | {comp:<18.4f} | {raw_struct:<15.4f} | {tf:<10.4f} | {sem_str:<20} | {str(is_hp):<10}")
        
        # Verify normalization bounds
        if not (0.0 <= comp <= 1.0):
            print(f"ERROR: Normalized composite score {comp} for {cid} is out of bounds [0.0, 1.0]")
            errors += 1
            
    print("=" * 165)
    if errors > 0:
        print("Composite Scorer Pipeline Verification FAILED.")
        sys.exit(1)
    else:
        print("Composite Scorer Pipeline Verification PASSED! Full system functions correctly.")

if __name__ == "__main__":
    main()

