# Redrob Ranker: Intelligent Candidate Ranking System

Redrob Ranker is a high-performance, modular candidate ranking system built for the Redrob Hackathon. It is designed to parse, score, and rank large candidate pools (up to 100,000+ candidates) in under 5 minutes on standard CPU-only hardware, without requiring network access.

The system evaluates candidates against the job description: **Senior AI Engineer — Founding Team at Redrob AI**.

---

## 🚀 Key Features

- **High-Performance Parsing**: Streams candidate profiles from raw `.jsonl` or `.jsonl.gz` files, handling malformed lines gracefully and efficiently.
- **Multidimensional Scoring Framework**: Evaluates candidates across five critical domains:
  1. **Skills Fit** (Weighted match, proficiency, endorsements, and assessments).
  2. **Career Trajectory** (Seniority, consulting company penalties, product company bonuses, and open-source contributions).
  3. **Experience Relevance** (Ideal vs. soft experience ranges, over-experience controls).
  4. **Location Fit** (Tier-based geographical scoring and relocation adjustments).
  5. **Education Quality** (Degree type, field of study alignment, and institution tiering).
- **Keyword-Stuffer Trap**: Actively penalizes candidates who list an excessive number of skills (>25) to prevent gaming the ranker.
- **Zero-GPU / Offline Execution**: Runs entirely on CPU with a memory footprint of $\le$ 16 GB RAM and no external API dependencies.

---

## 📁 Repository Structure

```text
redrob-ranker/
├── .gitignore               # Excludes python virtualenv, IDE configs, system logs, etc.
├── README.md                # Comprehensive documentation (this file)
├── requirements.txt         # Project dependencies (torch CPU-only, pandas, scikit-learn, etc.)
├── submission_metadata.yaml # Submission metadata for the hackathon
├── data/
│   └── sample_candidates.json # Sample candidate dataset for testing
├── ranker/
│   ├── __init__.py          # Exposes scorers and configurations
│   ├── data_loader.py       # JSONL stream loader and batching module
│   ├── jd_config.py         # Job description text and criteria configurations
│   ├── skills_scorer.py     # Matches skill requirements, proficiency, and assessments
│   ├── career_scorer.py     # Scores job titles, career progression, and company pedigree
│   ├── experience_scorer.py # Scores years of experience against target ranges
│   ├── location_scorer.py   # Scores Tier 1 / Tier 2 city proximity and relocation
│   └── education_scorer.py  # Evaluates degree levels, STEM fields, and school tiering
└── scripts/
    ├── explore.py           # Exploratory script showing candidate profile distributions
    └── test_scorers.py      # Verification script to test all modular scorers
```

---

## ⚙️ Setup and Installation

1. **Create and Activate a Virtual Environment**:
   ```bash
   # Create a virtual environment
   python -m venv .venv
   
   # Activate on Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   
   # Activate on Windows (CMD)
   .\.venv\Scripts\activate.bat
   
   # Activate on Unix/macOS
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🏃 Running the Scripts

The system includes two pre-built scripts for verification and exploration:

### 1. Run Verification & Test Scorers
Verify that all scorers yield outputs within bounds (`[0.0, 1.0]`):
```bash
python scripts/test_scorers.py data/sample_candidates.json
```
*(Alternatively, use `.\.venv\Scripts\python.exe scripts/test_scorers.py data/sample_candidates.json` if running directly).*

### 2. Candidate Data Exploration
Explore candidate distributions (countries, job titles, and experience metrics) in the sample dataset:
```bash
python scripts/explore.py data/sample_candidates.json
```

---

## 🧠 Scoring System Details

### 1. Skills Scorer (`SkillsScorer`)
Matches skills listed in candidate profiles against required and nice-to-have skills.
- **Required Skill Match**: Base score $1.0$ per match.
- **Nice-To-Have Skill Match**: Base score $0.5$ per match.
- **Proficiency Multiplier**:
  - `expert`: $1.0$ | `advanced`: $0.9$ | `intermediate`: $0.75$ | `beginner`: $0.5$
- **Trust Multiplier**: Scaled by endorsements up to 100: $\text{mult} = \min(1.0, 0.7 + \frac{\text{endorsements}}{100})$.
- **Duration Multiplier**: Normalized based on duration in months: $\min(1.0, \frac{\text{months}}{24})$.
- **Assessment Bonus**: Up to $+0.2$ bonus for verified skills assessments.
- **Keyword Stuffing Trap**: If the profile lists $>25$ skills, a penalty is applied: $\text{score} = \text{score} \times \max(0.7, 1.0 - (\text{skills\_count} - 25) \times 0.01)$.

### 2. Career Scorer (`CareerScorer`)
Evaluates the candidate's career trajectory. The final score is a weighted combination of:
- **Title Score (45%)**: Matching target titles ("AI Engineer", "ML Engineer", "Data Scientist", etc.). Non-AI titles (like "HR Manager", "Operations Manager") receive a sharp penalty.
- **Company Pedigree (30%)**: Consulting-fraction penalty. Candidates coming from large Indian consulting firms (TCS, Wipro, Infosys, etc.) are penalized proportionally to the duration spent there.
- **Career Progression (15%)**: Evaluates promotion trajectories (climbing seniority levels) and flags career stagnation (staying at one company for $\ge 10$ years without title progression).
- **Product Company Bonus (Up to +0.30)**: Bonus score for SaaS, E-commerce, AI/ML, and tech startup backgrounds.
- **Open-source & LinkedIn Bonus (Up to +0.07)**: Bonus for Github activity score $>50$ and verified LinkedIn connections.

### 3. Experience Scorer (`ExperienceScorer`)
Aligns years of experience (YOE) with the JD requirements:
- **Ideal Range (5–9 years)**: Score $1.0$.
- **Soft Boundaries (4–10 years)**: Linearly interpolated from $0.75$ to $1.0$ (e.g., 4 YOE = $0.75$, 10 YOE = $0.75$).
- **Outside Bounds**: Decreases by $0.1$ per year away from the soft boundaries.
- **Seniority Cap**: Candidates with $>15$ years of experience are capped at a maximum of $0.55$ to filter out over-qualified/expensive profiles.

### 4. Location Scorer (`LocationScorer`)
Evaluates proximity to the hybrid office locations (Pune/Noida, India):
- **Tier 1 Cities (India)**: Pune, Noida, Delhi, NCR, Gurugram, Gurgaon $\rightarrow$ Score $1.0$.
- **Tier 2 Cities (India)**: Hyderabad, Mumbai, Bangalore, Chennai, etc. $\rightarrow$ Score $0.85$.
- **Other Cities (India)**: Score $0.65$.
- **Outside India**: Score $0.30$ ($0.40$ if willing to relocate).
- **Relocation Adjustment**: Willingness to relocate adds a $+0.10$ bonus (capped at $1.0$).

### 5. Education Scorer (`EducationScorer`)
Scores the candidate's highest academic qualification:
- **Degree Tier**: PhD ($1.0$) | Master's ($0.9$) | Bachelor's ($0.75$) | Diploma ($0.5$).
- **Field of Study**: CS/AI/ECE ($1.0$) | Math/Stats/Physics ($0.85$) | Other STEM ($0.7$) | Non-STEM ($0.5$).
- **University Tier**: Tier 1 schools (IITs, NITs, BITS, etc.) receive a $+0.15$ bonus; Tier 2 receives a $+0.07$ bonus.

---

## ⏱️ Technical Constraints
- **Hardware**: CPU Only, $\le$ 16 GB RAM.
- **Network**: Completely offline (no external HTTP calls allowed).
- **Execution Time**: The ranker runs in $\le$ 5 minutes for a pool of 100k candidates.
