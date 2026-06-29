# Redrob Ranker: Intelligent Candidate Ranking System

Redrob Ranker is a high-performance, modular candidate ranking system built for the Redrob Hackathon. It is designed to parse, score, and rank large candidate pools (up to 100,000+ candidates) in under 5 minutes on standard CPU-only hardware, without requiring network access.

The system evaluates candidates against the job description: **Senior AI Engineer - Founding Team at Redrob AI**.

---

## 🚀 Key Features

- **High-Performance Parsing**: Streams candidate profiles from raw `.jsonl` or `.jsonl.gz` files, handling malformed lines gracefully and efficiently.
- **Multidimensional Scoring Framework**: Evaluates candidates across five critical structural domains plus behavioral and semantic layers:
  1. **Skills Fit** (Weighted match, proficiency, endorsements, and assessments).
  2. **Career Trajectory** (Seniority, consulting company penalties, product company bonuses, and open-source contributions).
  3. **Experience Relevance** (Ideal vs. soft experience ranges, over-experience controls).
  4. **Location Fit** (Tier-based geographical scoring and relocation adjustments).
  5. **Education Quality** (Degree type, field of study alignment, and institution tiering).
- **Behavioral Multiplier**: Factoring in candidate availability, platform activity recency, responsiveness rates, and profile completeness.
- **Honeypot Detection Anomaly Filter**: Automatically flags profile timeline inconsistencies, impossible job durations, expert skill inflation, and impossible response rates, downweighting suspected fake candidates.
- **Two-Stage Semantic Matcher**: Integrates fast TF-IDF matching across the full pool followed by lazy-loaded `SentenceTransformer` CPU-based re-ranking on the top candidates.
- **Zero-GPU / Offline Execution**: Runs entirely on CPU with a memory footprint of $\le$ 16 GB RAM and no external API dependencies.

---

## 📁 Repository Structure

```text
redrob-ranker/
├── .gitignore                 # Excludes python virtualenv, IDE configs, system logs, etc.
├── README.md                  # Comprehensive documentation (this file)
├── requirements.txt           # Project dependencies (torch CPU-only, pandas, scikit-learn, etc.)
├── submission_metadata.yaml   # Submission metadata for the hackathon
├── rank.py                    # Main CLI entry point for the submission pipeline
├── validate_submission.py     # Checks CSV compliance against hackathon guidelines
├── data/
│   └── sample_candidates.json # Sample candidate dataset for testing
├── sandbox/
│   └── app.py                 # Streamlit web dashboard for visual sandbox testing
├── ranker/
│   ├── __init__.py            # Exposes scorers, detectors, and configurations
│   ├── data_loader.py         # JSONL stream loader and batching module
│   ├── jd_config.py           # Job description text and criteria configurations
│   ├── skills_scorer.py       # Matches skill requirements, proficiency, and assessments
│   ├── career_scorer.py       # Scores job titles, career progression, and company pedigree
│   ├── experience_scorer.py   # Scores years of experience against target ranges
│   ├── location_scorer.py     # Scores Tier 1 / Tier 2 city proximity and relocation
│   ├── education_scorer.py    # Evaluates degree levels, STEM fields, and school tiering
│   ├── behavioral_scorer.py   # Computes availability and responsiveness multipliers
│   ├── honeypot_detector.py   # Detects profile inconsistencies and data corruption
│   ├── semantic_scorer.py     # Computes TF-IDF similarity and SentenceTransformer re-rankings
│   ├── composite_scorer.py    # Blends all sub-scores, applies multipliers, and normalizes
│   ├── reasoning_generator.py # Compiles grounded, natural language ranked reasonings
│   └── output_writer.py       # Exports top 100 candidates to structured CSV files
└── scripts/
    ├── explore.py             # Exploratory script showing candidate profile distributions
    └── test_scorers.py        # Verification script to test all modular scorers
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

## 🏃 Running the Project

The system contains command-line interfaces and an interactive dashboard for evaluation:

### 1. Running the Main Ranking CLI (`rank.py`)

This is the primary script that executes the ranking pipeline and writes output CSV files.

* **Run on sample candidate array (JSON)** (includes auto-validation):
  ```bash
  python rank.py --candidates data/sample_candidates.json --out submission.csv --sample --validate
  ```
* **Run on full candidate database (JSONL)**:
  ```bash
  python rank.py --candidates data/candidates.jsonl --out submission.csv --validate
  ```

### 2. Running the Streamlit Sandbox Dashboard (`sandbox/app.py`)

To launch the interactive visual evaluation board:

```bash
streamlit run sandbox/app.py
```

This opens the dashboard at **`http://localhost:8501`**, where you can upload `.json` or `.jsonl` pools, tweak limits, toggle Stage B transformers, inspect individual candidate score layers via Plotly charts, and download the ranked CSV.

### 3. Running Verification and Exploration Scripts

* **Verification script** (Tests individual module bounds):
  ```bash
  python scripts/test_scorers.py data/sample_candidates.json
  ```
* **Candidate distribution explorer**:
  ```bash
  python scripts/explore.py data/sample_candidates.json
  ```

---

## 🧠 Scoring System Details

### 1. Structural Scorers (Weight: 100% of Structural Score)

* **Skills Scorer (`SkillsScorer`)** [Weight: 30%]:
  - Required skills match $\rightarrow$ Base $1.0$; Nice-to-have match $\rightarrow$ Base $0.5$.
  - Proficiency multipliers: `expert` ($1.0$), `advanced` ($0.9$), `intermediate` ($0.75$), `beginner` ($0.5$).
  - Multiplier adjustments for endorsements ($\min(1.0, 0.7 + \frac{\text{ends}}{100})$) and duration ($\min(1.0, \frac{\text{months}}{24})$).
  - Assessment score bonuses up to $+0.2$.
  - Keyword stuffing penalty: listing $>25$ skills penalizes the score.
* **Career Scorer (`CareerScorer`)** [Weight: 35%]:
  - Title score: matching target engineering roles. Non-AI titles get penalized.
  - Company pedigree: penalizes candidates coming from major IT consulting firms (TCS, Infosys, Wipro, etc.) based on duration fraction.
  - Career progression: rewards promotions (seniority level increases) and flags career stagnation ($\ge 10$ years at one firm with no title changes).
  - Product company bonuses up to $+0.30$.
  - Open-source and LinkedIn bonuses up to $+0.07$.
* **Experience Scorer (`ExperienceScorer`)** [Weight: 15%]:
  - Ideal range (5–9 YOE) $\rightarrow$ Score $1.0$.
  - Soft boundaries (4–10 YOE) $\rightarrow$ Linearly mapped between $0.75$ and $1.0$.
  - Over-experience cap: candidates with $>15$ YOE are capped at $0.55$.
* **Location Scorer (`LocationScorer`)** [Weight: 10%]:
  - Tier 1 preferred cities (Pune/Noida/NCR/Delhi/Gurgaon) $\rightarrow$ Score $1.0$.
  - Tier 2 cities (Hyderabad/Mumbai/Bangalore/Chennai) $\rightarrow$ Score $0.85$.
  - Willingness to relocate adds a $+0.10$ bonus.
* **Education Scorer (`EducationScorer`)** [Weight: 10%]:
  - Degree tier: PhD ($1.0$) | Masters ($0.9$) | Bachelors ($0.75$).
  - Field relevance: CS/AI ($1.0$) | Math/Physics ($0.85$) | non-STEM ($0.5$).
  - Institution tier bonuses: Tier 1 (+0.15) | Tier 2 (+0.07).

### 2. Behavioral Scorer (`BehavioralScorer`)

Acts as a multiplier in `[0.3, 1.2]` applied on top of blended scores.

* **Availability (35%)**: Calculates `open_to_work_flag` (True: 1.0, False: 0.5), platform login recency (1.0 for $\le$14 days, down to 0.15 for 180+ days), and applications submitted.
* **Responsiveness (30%)**: Compares `recruiter_response_rate` (0–1), `avg_response_time_hours` buckets (0–24h up to 336h+), and `interview_completion_rate` (0–1).
* **Engagement (20%)**: Based on `profile_completeness_score`, verified email/phone, LinkedIn connectivity, and recruiter saves.
* **Notice Period Penalty**: Multiplier penalty for notice days ($0$ days: 1.05 bonus, 1–30: 1.0, 90: 0.88, 120+: 0.70).
* **Offer Acceptance Rate (15%)**: Maps candidate acceptance history, defaulting to neutral 0.7 if no history is present.

### 3. Honeypot Detector (`HoneypotDetector`)

Checks for impossible profile inconsistencies. Suspected candidates receive a multiplier of `0.01` (placing them at the bottom of rankings).

* **Timeline Inconsistency**: Checks if career roles start before college graduation.
* **Company Existence**: Checks if claimed duration at a role exceeds its calendar existence.
* **Skill Expert Inflation**: Identifies candidates listing $\ge 5$ "expert" skills with $0$ endorsements and $0$ duration.
* **Experience Overflow**: Checks if total career history duration exceeds claimed years of experience.
* **Impossible Values**: Flags out-of-bounds rates (e.g. response rate $>1.0$ or acceptance rates outside `[-1, 1]`).
* **Orphaned Assessments**: Checks if candidate completed $>8$ skill assessments for skills not listed on their profile.

### 4. Semantic Scorer & Blending (`SemanticScorer` & `CompositeScorer`)

* **TF-IDF Blending (Stage A)**: Matches full candidate text corpus against the job description text, blending it as: $\text{blend} = \text{structural} \times 0.75 + \text{tfidf} \times 0.25$.
* **Transformer Re-ranking (Stage B)**: Re-ranks top-N candidates using the lightweight `all-MiniLM-L6-v2` transformer model on CPU, blending it as: $\text{blend} = \text{structural} \times 0.60 + \text{tfidf} \times 0.20 + \text{semantic} \times 0.20$.

---

## ⏱️ Technical Constraints

- **Hardware**: CPU Only, $\le$ 16 GB RAM.
- **Network**: Completely offline (no external HTTP calls allowed).
- **Execution Time**: The ranker runs in $\le$ 5 minutes for a pool of 100k candidates.

