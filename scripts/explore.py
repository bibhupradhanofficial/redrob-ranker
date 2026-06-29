import sys
import os
import pandas as pd
import numpy as np
from collections import Counter
from dateutil import parser
from datetime import datetime

# Add parent directory to sys.path to allow imports from ranker
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ranker.data_loader import DataLoader

def get_years_of_experience(c: dict) -> float:
    # 1. Check direct keys (checking profile first, then root)
    profile = c.get("profile") or {}
    for d in [profile, c]:
        for key in ["years_of_experience", "years_experience", "experience_years"]:
            if key in d and d[key] is not None:
                try:
                    return round(float(d[key]), 1)
                except (ValueError, TypeError):
                    pass
                
    # 2. Compute from career history
    history = c.get("career_history") or []
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
            start_date = parser.parse(str(start_str))
            if end_str:
                end_date = parser.parse(str(end_str))
            else:
                end_date = datetime.now()
            
            delta = end_date - start_date
            total_days += max(0, delta.days)
        except Exception:
            pass
            
    if total_days > 0:
        return round(total_days / 365.25, 1)
    return 0.0

def print_stat_row(name: str, values: list):
    if not values:
        print(f"{name:<30} | {'N/A':>10} | {'N/A':>10} | {'N/A':>10}")
        return
    mean_val = np.mean(values)
    min_val = np.min(values)
    max_val = np.max(values)
    print(f"{name:<30} | {mean_val:>10.2f} | {min_val:>10.2f} | {max_val:>10.2f}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/explore.py <path_to_candidates_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' does not exist.")
        sys.exit(1)

    print(f"Initializing DataLoader with: {filepath}")
    loader = DataLoader(filepath)
    
    # Load first 50 candidates
    candidates = loader.load_all(max_candidates=50)
    num_loaded = len(candidates)
    print(f"Successfully loaded {num_loaded} candidates.\n")

    if num_loaded == 0:
        print("No candidates found in the provided file.")
        return

    # 1. Prepare Summary Table Data
    table_rows = []
    recruiter_response_rates = []
    interview_completion_rates = []
    github_activity_scores = []
    notice_periods = []
    countries = []
    titles = []

    for c in candidates:
        candidate_id = c.get("candidate_id") or c.get("id") or "N/A"
        profile = c.get("profile") or {}
        redrob_signals = c.get("redrob_signals") or {}
        
        current_title = (
            profile.get("current_title")
            or c.get("current_title")
            or profile.get("title")
            or c.get("title")
            or "N/A"
        )
        yoe = get_years_of_experience(c)
        
        country = profile.get("country") or c.get("country") or ""
        if not country and isinstance(profile.get("location"), dict):
            country = profile.get("location").get("country") or ""
        if not country and isinstance(c.get("location"), dict):
            country = c.get("location").get("country") or ""
        if not country:
            country = "Unknown"
            
        open_to_work = redrob_signals.get("open_to_work_flag")
        if open_to_work is None:
            open_to_work = redrob_signals.get("open_to_work")
        if open_to_work is None:
            open_to_work = c.get("open_to_work_flag")
        if open_to_work is None:
            open_to_work = c.get("open_to_work")
        if open_to_work is None:
            open_to_work = False
            
        notice_days = (
            redrob_signals.get("notice_period_days")
            or redrob_signals.get("notice_period")
            or c.get("notice_period_days")
            or c.get("notice_period")
            or 0
        )
        
        # Skills parsing
        skills = c.get("skills") or []
        skill_names = []
        if isinstance(skills, list):
            for s in skills:
                if isinstance(s, dict):
                    name = s.get("name") or s.get("skill_name") or ""
                else:
                    name = str(s)
                if name:
                    skill_names.append(name)
        elif isinstance(skills, str):
            skill_names = [s.strip() for s in skills.split(",") if s.strip()]
        
        top_3_skills = ", ".join(skill_names[:3]) if skill_names else "None"

        table_rows.append({
            "candidate_id": candidate_id,
            "current_title": current_title,
            "years_of_experience": yoe,
            "country": country,
            "open_to_work_flag": open_to_work,
            "notice_period_days": notice_days,
            "top_3_skills": top_3_skills
        })

        # Collect metrics for stats
        rr = redrob_signals.get("recruiter_response_rate")
        if rr is None:
            rr = c.get("recruiter_response_rate")
        if rr is not None:
            try:
                recruiter_response_rates.append(float(rr))
            except (ValueError, TypeError):
                pass

        icr = redrob_signals.get("interview_completion_rate")
        if icr is None:
            icr = c.get("interview_completion_rate")
        if icr is not None:
            try:
                interview_completion_rates.append(float(icr))
            except (ValueError, TypeError):
                pass

        gas = redrob_signals.get("github_activity_score")
        if gas is None:
            gas = c.get("github_activity_score")
        if gas is not None:
            try:
                github_activity_scores.append(float(gas))
            except (ValueError, TypeError):
                pass

        notice_periods.append(float(notice_days))
        countries.append(country)
        titles.append(current_title)

    # 2. Print Summary Table
    df = pd.DataFrame(table_rows)
    print("=" * 100)
    print("CANDIDATE SUMMARY TABLE (First 50 Candidates)")
    print("=" * 100)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_rows', 100)
    print(df.to_string(index=False))
    print("\n")

    # 3. Print Signal Distribution Stats
    print("=" * 100)
    print("SIGNAL DISTRIBUTION STATS")
    print("=" * 100)
    print(f"{'Metric':<30} | {'Mean':>10} | {'Min':>10} | {'Max':>10}")
    print("-" * 70)
    print_stat_row("recruiter_response_rate", recruiter_response_rates)
    print_stat_row("interview_completion_rate", interview_completion_rates)
    print_stat_row("github_activity_score", github_activity_scores)
    print_stat_row("notice_period_days", notice_periods)
    print("\n")

    # 4. Print Candidate Count by Country
    print("=" * 100)
    print("CANDIDATES BY COUNTRY")
    print("=" * 100)
    country_counts = Counter(countries)
    for country, count in country_counts.most_common():
        print(f"{country:<30}: {count}")
    print("\n")

    # 5. Print Most Common Titles
    print("=" * 100)
    print("MOST COMMON CURRENT TITLES")
    print("=" * 100)
    title_counts = Counter(titles)
    for title, count in title_counts.most_common(10):
        print(f"{title:<50}: {count}")
    print("=" * 100)

if __name__ == "__main__":
    main()
