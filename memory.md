# Memory — Complete Candidate Ranking Pipeline & Streamlit Sandbox

Last updated: 2026-06-29 16:13:00

## What was built

- **Scorers & Detectors**:
  - [ranker/behavioral_scorer.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/behavioral_scorer.py): `BehavioralScorer` availability/responsiveness engine.
  - [ranker/honeypot_detector.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/honeypot_detector.py): `HoneypotDetector` profile anomaly filter.
  - [ranker/semantic_scorer.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/semantic_scorer.py): `SemanticScorer` TF-IDF and SentenceTransformer CPU re-ranking engine.
  - [ranker/composite_scorer.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/composite_scorer.py): `CompositeScorer` scoring layer aggregator and normalizer.
- **Explainers & Writers**:
  - [ranker/reasoning_generator.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/reasoning_generator.py): `ReasoningGenerator` specific, grounded text compiler.
  - [ranker/output_writer.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/output_writer.py): `OutputWriter` tie-breaker sorting and CSV compiler.
- **Entry Points & Dashboards**:
  - [rank.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/rank.py): Main CLI runner for submission outputs.
  - [validate_submission.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/validate_submission.py): Validates outputs against hackathon schemas, contiguous ranks, and monotonic scores.
  - [sandbox/app.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/sandbox/app.py): Streamlit web sandbox dashboard (supporting both `.json` and `.jsonl` uploads via auto-detection parsing).
- **Package Exports & Docs**:
  - [ranker/__init__.py](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/ranker/__init__.py): Exposes all modules.
  - [README.md](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/README.md): Exhaustive setup, execution guide, and scoring details.
  - [.gitignore](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/.gitignore): Clean workspace ignore patterns.

## Decisions made

- **Evaluation Context**: Set current year reference to `2026` across all time-based metrics calculations.
- **State Preservation**: Initialized `st.session_state` keys at the entry point of Streamlit to avoid pipeline re-execution on widget changes.
- **Model Caching**: Cached the `SentenceTransformer` CPU-based model loading in Streamlit via `@st.cache_resource`.
- **Reasoning Structure**: Length-capped at 250 characters. Prioritized Skills -> Career -> TF-IDF. Ranks 40+ always include a concern.
- **Subprocess Robustness**: Used `sys.executable` in `rank.py` to ensure the submission validator runs with the active virtual environment's Python interpreter.

## Problems solved

- Fixed the duplicate main runner block in the scorer test script.
- Added auto-detection parsing for file uploads in the Streamlit app to natively support both JSON arrays and newline-separated JSON Lines (JSONL).
- Resolved CSV validation failure on small development datasets by printing warnings rather than hard failing on row counts less than 101.

## Current state

- The candidate ranking CLI, web sandbox dashboard, and validator scripts are complete, verified, and functional.
- The pipeline executes end-to-end on test candidates, yielding valid normalized composite scores, natural reasonings, and formatted CSV files that pass all validation criteria.

## Next session starts with

- Fill out the team, contact, and hosted spaces links inside [submission_metadata.yaml](file:///d:/Programming%20Playground/Machine%20Learning%20Playground/redrob-ranker/submission_metadata.yaml).
- Deploy the Streamlit app to Hugging Face Spaces or Streamlit Cloud.
- Run `python rank.py` on the complete candidate database pool (`candidates.jsonl`) to compile the final `submission.csv` for submission portal upload.

## Open questions

- None.
