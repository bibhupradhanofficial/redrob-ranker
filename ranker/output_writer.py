import csv
import logging

logger = logging.getLogger(__name__)

class OutputWriter:
    """Writes the final ranked CSV and validates it."""

    def write(
        self,
        ranked_results: list[dict],
        candidates_by_id: dict[str, dict],
        reasonings: dict[str, str],
        output_path: str,
        participant_id: str = "team_bibhu"
    ):
        """
        Takes:
        - ranked_results: sorted list from CompositeScorer (all candidates)
        - candidates_by_id: dict mapping candidate_id -> candidate dict
        - reasonings: dict mapping candidate_id -> reasoning string
        - output_path: path to write the CSV file

        Writes top-100 to CSV with columns: candidate_id, rank, score, reasoning
        Ensures:
        - Scores are monotonically non-increasing (rank 1 has highest score)
        - Scores are rounded to 6 decimal places
        - Tie-breaking: equal scores -> candidate_id ascending
        - Reasoning is CSV-safe (strip newlines, escape commas)
        - UTF-8 encoding
        """
        # Apply strict sorting with tie-breaker:
        # Score descending (-score), then candidate_id ascending
        sorted_results = sorted(
            ranked_results,
            key=lambda x: (-x["composite_score"], x["candidate_id"])
        )

        top100 = sorted_results[:100]
        rows = []
        for rank_idx, r in enumerate(top100, start=1):
            cid = r["candidate_id"]
            score = round(r["composite_score"], 6)
            reason = reasonings.get(cid, "")
            
            # Sanitize reasoning: remove newlines and carriage returns
            reason = reason.replace("\n", " ").replace("\r", " ").strip()
            rows.append([cid, rank_idx, score, reason])

        # Write CSV file
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            writer.writerows(rows)

        logger.info(f"Successfully wrote {len(rows)} rows to {output_path}")
        print(f"Written {len(rows)} rows to {output_path}")
