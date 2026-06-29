import csv
import sys
import re
import os

def validate(filepath: str) -> bool:
    if not os.path.exists(filepath):
        print(f"ERROR: File '{filepath}' does not exist.")
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except Exception as e:
        print(f"ERROR: Failed to read CSV file: {e}")
        return False

    # Check row count
    if len(rows) > 101:
        print(f"ERROR: Expected at most 101 rows (including header), found {len(rows)}.")
        return False
    elif len(rows) < 2:
        print("ERROR: CSV is empty or has no candidate rows.")
        return False
    elif len(rows) < 101:
        print(f"WARNING: CSV contains only {len(rows)} rows (including header). Final submission requires exactly 101 rows. Proceeding with validation for available records...")


    # Check header
    header = rows[0]
    expected_header = ["candidate_id", "rank", "score", "reasoning"]
    if header != expected_header:
        print(f"ERROR: Header mismatch. Expected {expected_header}, found {header}.")
        return False

    last_score = float("inf")
    candidate_id_pattern = re.compile(r"^CAND_\d+$")

    for i, row in enumerate(rows[1:], start=1):
        if len(row) != 4:
            print(f"ERROR on row {i+1}: Expected 4 columns, found {len(row)}.")
            return False

        cid, rank_str, score_str, reasoning = row

        # Check empty values
        if not cid.strip() or not rank_str.strip() or not score_str.strip() or not reasoning.strip():
            print(f"ERROR on row {i+1}: Found empty/missing values in column.")
            return False

        # Validate candidate_id format
        if not candidate_id_pattern.match(cid):
            print(f"ERROR on row {i+1}: Invalid candidate_id format: '{cid}' (expected 'CAND_XXXXXX').")
            return False

        # Validate rank value and continuity
        try:
            rank = int(rank_str)
            if rank != i:
                print(f"ERROR on row {i+1}: Rank continuity broken. Expected rank {i}, found {rank}.")
                return False
        except ValueError:
            print(f"ERROR on row {i+1}: Invalid rank value '{rank_str}' (expected integer).")
            return False

        # Validate score value and non-increasing order
        try:
            score = float(score_str)
            if not (0.0 <= score <= 1.0):
                print(f"ERROR on row {i+1}: Score {score} is out of bounds [0.0, 1.0].")
                return False
            
            # Monotonically non-increasing check (tolerance for rounding)
            if score > last_score + 1e-9:
                print(f"ERROR on row {i+1}: Score ordering is not non-increasing. Previous: {last_score}, Current: {score}.")
                return False
            last_score = score
        except ValueError:
            print(f"ERROR on row {i+1}: Invalid score value '{score_str}' (expected float).")
            return False

        # Validate reasoning text length and constraints
        if len(reasoning) > 250:
            print(f"ERROR on row {i+1}: Reasoning exceeds 250 characters (length: {len(reasoning)}).")
            return False

    print("VALIDATION PASSED: CSV is correctly formatted and meets all guidelines.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_submission.py <path_to_csv>")
        sys.exit(1)
    
    success = validate(sys.argv[1])
    if not success:
        sys.exit(1)
    sys.exit(0)
