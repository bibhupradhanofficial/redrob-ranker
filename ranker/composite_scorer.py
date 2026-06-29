import logging
from tqdm import tqdm
from ranker.skills_scorer import SkillsScorer
from ranker.career_scorer import CareerScorer
from ranker.experience_scorer import ExperienceScorer
from ranker.location_scorer import LocationScorer
from ranker.education_scorer import EducationScorer
from ranker.behavioral_scorer import BehavioralScorer
from ranker.honeypot_detector import HoneypotDetector
from ranker.semantic_scorer import SemanticScorer

logger = logging.getLogger(__name__)

class CompositeScorer:
    """
    Combines all individual scores into a final composite score.

    Architecture:
    1. Compute structural score = weighted sum of SkillsScorer, CareerScorer,
       ExperienceScorer, LocationScorer, EducationScorer.
    2. Apply BehavioralScorer multiplier.
    3. Apply HoneypotDetector multiplier.
    4. Add TF-IDF semantic score (blended in).
    5. (Optional) Add sentence-transformer semantic score for top-N.
    """

    def __init__(
        self,
        use_semantic: bool = True,
        semantic_top_n: int = 1500
    ):
        self.skills = SkillsScorer()
        self.career = CareerScorer()
        self.experience = ExperienceScorer()
        self.location = LocationScorer()
        self.education = EducationScorer()
        self.behavioral = BehavioralScorer()
        self.honeypot = HoneypotDetector()
        self.semantic = SemanticScorer(use_semantic=use_semantic)
        self.semantic_top_n = semantic_top_n

    def score_all(self, candidates: list[dict]) -> list[dict]:
        """
        Main method. Takes the full candidate list.
        Returns list of dicts sorted by composite_score descending:
        [
          {
            "candidate_id": str,
            "composite_score": float,
            "skills_score": float,
            "career_score": float,
            "experience_score": float,
            "location_score": float,
            "education_score": float,
            "behavioral_multiplier": float,
            "tfidf_score": float,
            "semantic_score": float or None,
            "is_honeypot": bool,
            "raw_structural": float,
          },
          ...
        ]
        """
        if not candidates:
            return []

        # Step 1: Fit TF-IDF on all candidates
        logger.info("Fitting TF-IDF on candidate pool...")
        self.semantic.fit(candidates)
        tfidf_scores = self.semantic.tfidf_scores()

        # Step 2: Compute structural scores for all candidates (with tqdm)
        logger.info("Computing structural scores...")
        results = []
        for c in tqdm(candidates, desc="Scoring candidates"):
            cid = c.get("candidate_id") or c.get("id") or "N/A"
            sk = self.skills.score(c)
            ca = self.career.score(c)
            ex = self.experience.score(c)
            lo = self.location.score(c)
            ed = self.education.score(c)
            bm = self.behavioral.score(c)
            hp_mult = self.honeypot.honeypot_multiplier(c)
            is_hp = self.honeypot.is_honeypot(c)
            tf = tfidf_scores.get(cid, 0.0)

            structural = (0.30 * sk + 0.35 * ca + 0.15 * ex
                          + 0.10 * lo + 0.10 * ed)
            blend = structural * 0.75 + tf * 0.25
            composite = blend * bm * hp_mult

            results.append({
                "candidate_id": cid,
                "composite_score": composite,
                "raw_structural": structural,
                "skills_score": sk,
                "career_score": ca,
                "experience_score": ex,
                "location_score": lo,
                "education_score": ed,
                "behavioral_multiplier": bm,
                "tfidf_score": tf,
                "semantic_score": None,
                "is_honeypot": is_hp,
            })

        # Step 3: Sort by composite_score and take top-N for semantic re-ranking
        results.sort(key=lambda x: x["composite_score"], reverse=True)

        if self.semantic.use_semantic and len(results) > 0:
            actual_top_n = min(len(results), self.semantic_top_n)
            logger.info(f"Running semantic re-ranking on top {actual_top_n}...")
            
            top_n_ids = {r["candidate_id"] for r in results[:actual_top_n]}
            top_n_candidates = [c for c in candidates if (c.get("candidate_id") or c.get("id") or "N/A") in top_n_ids]
            
            sem_scores = self.semantic.compute_semantic_scores(top_n_candidates)

            for r in results[:actual_top_n]:
                cid = r["candidate_id"]
                sem = sem_scores.get(cid, 0.0)
                r["semantic_score"] = sem
                
                # Re-blend with semantic
                structural = r["raw_structural"]
                tf = r["tfidf_score"]
                bm = r["behavioral_multiplier"]
                hp_mult = 0.01 if r["is_honeypot"] else 1.0
                
                blend = structural * 0.60 + tf * 0.20 + sem * 0.20
                r["composite_score"] = blend * bm * hp_mult

        # Step 4: Re-sort after semantic re-ranking
        results.sort(key=lambda x: x["composite_score"], reverse=True)

        # Step 5: Normalize scores to [0, 1]
        if results:
            max_s = results[0]["composite_score"]
            min_s = results[-1]["composite_score"]
            for r in results:
                if max_s != min_s:
                    r["composite_score"] = (r["composite_score"] - min_s) / (max_s - min_s)
                else:
                    r["composite_score"] = 1.0

        return results
