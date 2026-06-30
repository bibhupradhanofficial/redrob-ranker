#!/usr/bin/env python3
"""
rank.py — Redrob Hackathon Submission Entry Point

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv
    python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv
    python rank.py --candidates ./data/sample_candidates.json --out ./submission.csv [--sample]
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv --no-semantic

Options:
    --candidates PATH     Path to candidates file (.jsonl, .jsonl.gz, or .json for sample)
    --out PATH            Output CSV path (default: submission.csv)
    --no-semantic         Skip sentence-transformer step (faster, lower quality)
    --semantic-top-n N    Number of candidates for semantic re-ranking (default: 1500)
    --sample              Load as JSON array instead of JSONL (for sample_candidates.json)
    --max-candidates N    Limit candidates loaded (for testing; not for final submission)
    --validate            Run validate_submission.py after writing output
    --participant-id STR  Participant ID for filename (default: team_bibhu)
"""

import argparse
import time
import json
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker")
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out", default="submission.csv")
    parser.add_argument("--no-semantic", action="store_true")
    parser.add_argument("--semantic-top-n", type=int, default=500)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--participant-id", default="team_bibhu")
    args = parser.parse_args()

    start = time.time()
    print(f"[rank.py] Starting Redrob Ranker")
    print(f"[rank.py] Input: {args.candidates}")
    print(f"[rank.py] Output: {args.out}")
    print(f"[rank.py] Semantic re-ranking: {not args.no_semantic}")

    # --- Load candidates ---
    from ranker.data_loader import DataLoader
    loader = DataLoader(args.candidates)
    if args.sample:
        # Load as JSON array (for sample_candidates.json)
        with open(args.candidates, "r", encoding="utf-8") as f:
            candidates = json.load(f)
        if args.max_candidates:
            candidates = candidates[:args.max_candidates]
        print(f"[rank.py] Loaded {len(candidates)} candidates (sample mode)")
    else:
        candidates = loader.load_all(max_candidates=args.max_candidates)
        print(f"[rank.py] Loaded {len(candidates)} candidates")

    # Build lookup dict
    candidates_by_id = {c["candidate_id"]: c for c in candidates}

    # --- Score all candidates ---
    from ranker.composite_scorer import CompositeScorer
    scorer = CompositeScorer(
        use_semantic=not args.no_semantic,
        semantic_top_n=args.semantic_top_n
    )
    ranked_results = scorer.score_all(candidates)

    elapsed_scoring = time.time() - start
    print(f"[rank.py] Scoring complete in {elapsed_scoring:.1f}s")

    # --- Generate reasonings for top-100 ---
    from ranker.reasoning_generator import ReasoningGenerator
    reasoning_gen = ReasoningGenerator()
    top100 = ranked_results[:100]
    reasonings = {}
    for rank_idx, r in enumerate(top100, start=1):
        cid = r["candidate_id"]
        c = candidates_by_id[cid]
        reasonings[cid] = reasoning_gen.generate(c, r, rank_idx)

    # --- Write output ---
    from ranker.output_writer import OutputWriter
    writer = OutputWriter()
    writer.write(ranked_results, candidates_by_id, reasonings, args.out, args.participant_id)

    elapsed_total = time.time() - start
    print(f"[rank.py] Total time: {elapsed_total:.1f}s")
    print(f"[rank.py] Top-5 candidates:")
    for r in ranked_results[:5]:
        c = candidates_by_id[r["candidate_id"]]
        print(f"  Rank {ranked_results.index(r)+1}: {r['candidate_id']} - "
              f"{c['profile']['current_title']} @ {c['profile']['current_company']} "
              f"| score={r['composite_score']:.4f}")

    # --- Optional validation ---
    if args.validate:
        import subprocess
        result = subprocess.run(
            [sys.executable, "validate_submission.py", args.out],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print("VALIDATION FAILED:", result.stderr)

    if elapsed_total > 290:
        print(f"WARNING: Total time {elapsed_total:.0f}s is close to the 5-minute limit.")

if __name__ == "__main__":
    main()
