import os
import sys
import json
import time
import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# Insert parent directory to sys.path to allow imports from ranker
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ranker.composite_scorer import CompositeScorer
from ranker.reasoning_generator import ReasoningGenerator

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Redrob AI Candidate Ranker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------
# 🔒 st.cache_resource for SentenceTransformer Loading
# ----------------------------------------------------
@st.cache_resource
def load_transformer_model():
    """Loads and caches the SentenceTransformer model on CPU."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

# ----------------------------------------------------
# 🔋 Session State Initialization
# ----------------------------------------------------
if "uploaded_candidates" not in st.session_state:
    st.session_state.uploaded_candidates = None
if "ranked_results" not in st.session_state:
    st.session_state.ranked_results = None
if "candidates_by_id" not in st.session_state:
    st.session_state.candidates_by_id = None
if "reasonings" not in st.session_state:
    st.session_state.reasonings = None

# ----------------------------------------------------
# 🖥️ Sidebar Layout
# ----------------------------------------------------
st.sidebar.title("⚙️ Configuration")
enable_semantic = st.sidebar.toggle(
    "Enable Semantic Re-ranking (Stage B)",
    value=True,
    help="Runs sentence-transformer (all-MiniLM-L6-v2) on the top candidates. Takes ~15s to run on CPU."
)
max_candidates = st.sidebar.slider(
    "Max candidates to rank",
    min_value=10,
    max_value=100,
    value=100,
    help="Limits the number of candidate files processed for the sandbox run."
)

st.sidebar.divider()
st.sidebar.markdown("**Hardware & Constraints**")
st.sidebar.info("💻 CPU only | 🔒 Offline inference | ⏱️ Run limit <= 5 min")

# Link to repository and author info
st.sidebar.markdown("[GitHub Repository](https://github.com/bibhu-pradhan/redrob-ranker)")
st.sidebar.caption("Hackathon Team: **Team Bibhu Pradhan**")

# Serve sample candidate file directly from local data folder
sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'sample_candidates.json')
if os.path.exists(sample_path):
    with open(sample_path, "r", encoding="utf-8") as f:
        sample_data = f.read()
    st.sidebar.download_button(
        label="📥 Download Sample Candidates",
        data=sample_data,
        file_name="sample_candidates.json",
        mime="application/json"
    )

# ----------------------------------------------------
# 📄 Main Page Headers
# ----------------------------------------------------
st.title("Redrob AI Candidate Ranker - Hackathon Sandbox")
st.subheader("Position: Senior AI Engineer - Founding Team @ Redrob AI")

# Create main area tabs
tab1, tab2, tab3 = st.tabs(["Upload & Rank", "Results", "Score Breakdown"])

# ----------------------------------------------------
# Tab 1: Upload & Rank
# ----------------------------------------------------
with tab1:
    st.markdown("### Upload Candidates Dataset")
    st.info(
        "Upload a JSON array of candidate objects (e.g. `sample_candidates.json`). "
        "The schema must match the standard Redrob Candidate format (containing `candidate_id`, `profile`, `skills`, `career_history`, and `redrob_signals`)."
    )

    uploaded_file = st.file_uploader("Choose a candidate JSON or JSONL file", type=["json", "jsonl"])

    if uploaded_file is not None:
        try:
            file_contents = uploaded_file.getvalue().decode("utf-8")
            
            # Detect if it's a JSON array or JSON Lines
            first_char = ""
            for char in file_contents[:200]:
                if char.strip():
                    first_char = char
                    break
            
            data = None
            if first_char == '[':
                # Standard JSON Array
                parsed_val = json.loads(file_contents)
                if isinstance(parsed_val, list):
                    data = parsed_val
                else:
                    st.error("Invalid File Format: Uploaded JSON must be a list (array) of candidate objects.")
            else:
                # JSON Lines format
                data = []
                for line_num, line in enumerate(file_contents.splitlines(), start=1):
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    try:
                        data.append(json.loads(line_clean))
                    except json.JSONDecodeError as je:
                        st.error(f"JSON Decode Error on line {line_num}: {je}")
                        data = None
                        break
            
            if data is not None and len(data) > 0:
                st.session_state.uploaded_candidates = data
                st.success(f"Success! Loaded {len(data)} candidates from file.")
                
                # Show collapsed preview of the first candidate
                with st.expander("Preview First Candidate Record schema"):
                    st.json(data[0])
            elif data is not None and len(data) == 0:
                st.warning("Uploaded file is empty (contains 0 candidates).")
                st.session_state.uploaded_candidates = None
            else:
                st.session_state.uploaded_candidates = None
        except Exception as e:
            st.error(f"Error parsing candidates file: {e}")
            st.session_state.uploaded_candidates = None


    # Pipeline Run trigger
    run_disabled = (st.session_state.uploaded_candidates is None)
    if st.button("Run Ranker 🚀", disabled=run_disabled, type="primary"):
        # Streamlit status indicator
        with st.status("Initializing scoring pipeline...", expanded=True) as status:
            status.update(label="Extracting candidate features...")
            time.sleep(0.5)
            
            status.update(label="Computing candidate structural scores...")
            t0 = time.time()
            scorer = CompositeScorer(use_semantic=enable_semantic, semantic_top_n=max_candidates)
            
            # If semantic enabled, pre-load cached sentence transformer to bypass reload overhead
            if enable_semantic:
                status.update(label="Loading CPU Sentence-Transformers (Cached)...")
                model = load_transformer_model()
                scorer.semantic.semantic_model = model
                scorer.semantic.jd_embedding = model.encode(
                    [scorer.semantic.jd_text], convert_to_numpy=True, show_progress_bar=False
                )
            
            # Score ALL candidates to ensure TF-IDF and Normalization bounds are computed over the full pool
            all_ranked_results = scorer.score_all(st.session_state.uploaded_candidates)
            
            # Slice results to top max_candidates for UI display and details
            ranked_results = all_ranked_results[:max_candidates]
            
            status.update(label="Compiling natural-language justifications...")
            candidates_by_id = {c["candidate_id"]: c for c in st.session_state.uploaded_candidates}
            reasoning_gen = ReasoningGenerator()
            reasonings = {}
            for rank_idx, r in enumerate(ranked_results, start=1):
                cid = r["candidate_id"]
                c = candidates_by_id[cid]
                reasonings[cid] = reasoning_gen.generate(c, r, rank_idx)

            # Store in session state to persist across widgets redraw
            st.session_state.ranked_results = ranked_results
            st.session_state.candidates_by_id = candidates_by_id
            st.session_state.reasonings = reasonings
            
            elapsed = time.time() - t0
            status.update(label="Processing and ranking finished!", state="complete")
            
        st.success(f"✅ Scored {len(st.session_state.uploaded_candidates)} candidates and loaded top {len(ranked_results)} in {elapsed:.1f} seconds.")

# ----------------------------------------------------
# Tab 2: Results
# ----------------------------------------------------
with tab2:
    if st.session_state.ranked_results is None:
        st.warning("Please upload candidate data and click 'Run Ranker 🚀' in the 'Upload & Rank' tab first.")
    else:
        st.markdown("### Top Ranking Candidate Metrics")
        
        # Metrics row (Top 10 parameters)
        col1, col2, col3, col4 = st.columns(4)
        
        # col 1: top candidate
        top_cand = st.session_state.ranked_results[0]
        top_id = top_cand["candidate_id"]
        top_profile = st.session_state.candidates_by_id[top_id].get("profile") or {}
        col1.metric(
            "Top Candidate",
            f"{top_profile.get('current_title', 'N/A')}",
            help=f"ID: {top_id} @ {top_profile.get('current_company', 'N/A')}"
        )
        
        # col 2: avg score
        top10_scores = [r["composite_score"] for r in st.session_state.ranked_results[:10]]
        avg_score = np.mean(top10_scores) if top10_scores else 0.0
        col2.metric("Avg Score (Top 10)", f"{avg_score:.3f}")
        
        # col 3: India-based in top 10
        top10_india = 0
        for r in st.session_state.ranked_results[:10]:
            c = st.session_state.candidates_by_id[r["candidate_id"]]
            country = (c.get("profile") or {}).get("country") or c.get("country") or ""
            if country.strip().lower() == "india":
                top10_india += 1
        col3.metric("India-Based (Top 10)", f"{top10_india} / 10")
        
        # col 4: honeypots
        hp_count = sum(1 for r in st.session_state.ranked_results if r["is_honeypot"])
        col4.metric("Honeypots Flagged", f"{hp_count}")

        st.divider()
        st.markdown("### Ranked Candidate List")
        
        # Compile dataframe rows
        table_rows = []
        for rank_idx, r in enumerate(st.session_state.ranked_results, start=1):
            cid = r["candidate_id"]
            c = st.session_state.candidates_by_id[cid]
            profile = c.get("profile") or {}
            signals = c.get("redrob_signals") or {}
            
            country = profile.get("country") or c.get("country") or ""
            city = ""
            loc_val = profile.get("location") or c.get("location") or ""
            if isinstance(loc_val, dict):
                city = loc_val.get("city") or ""
                if not country:
                    country = loc_val.get("country") or ""
            else:
                city = str(loc_val)
            location = f"{city}, {country}" if city and country else (city or country or "Unknown")
            
            active_date = signals.get("last_active_date")
            is_active = "Yes" if active_date else "No"
            
            table_rows.append({
                "Rank": rank_idx,
                "Candidate ID": cid,
                "Current Title": profile.get("current_title") or c.get("current_title") or "N/A",
                "Company": profile.get("current_company") or c.get("current_company") or "N/A",
                "Yrs Exp": profile.get("years_of_experience") or c.get("years_of_experience") or 0.0,
                "Location": location,
                "Score": r["composite_score"],
                "Skills Score": r["skills_score"],
                "Career Score": r["career_score"],
                "Behavioral Mult": r["behavioral_multiplier"],
                "Active?": is_active,
                "Reasoning": st.session_state.reasonings.get(cid, "")
            })
            
        df_results = pd.DataFrame(table_rows)

        # Style function for color-coding scores
        def style_score(val):
            if val > 0.7:
                color = '#2ecc71'  # Green
            elif val >= 0.4:
                color = '#f39c12'  # Orange/Yellow
            else:
                color = '#e74c3c'  # Red
            return f'color: {color}; font-weight: bold;'

        # Render styled dataframe
        styled_df = df_results.style.map(style_score, subset=['Score']).format({
            "Score": "{:.4f}",
            "Skills Score": "{:.4f}",
            "Career Score": "{:.4f}",
            "Behavioral Mult": "{:.4f}",
            "Yrs Exp": "{:.1f}"
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # CSV Download button
        csv_buffer = io.StringIO()
        import csv
        writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for idx, r in enumerate(st.session_state.ranked_results, 1):
            cid = r["candidate_id"]
            score = round(r["composite_score"], 6)
            reason = st.session_state.reasonings.get(cid, "").replace("\n", " ").replace("\r", " ").strip()
            writer.writerow([cid, idx, score, reason])
            
        st.download_button(
            label="📥 Download Submission CSV",
            data=csv_buffer.getvalue(),
            file_name="submission.csv",
            mime="text/csv",
            type="secondary"
        )
        
        # Score distribution chart
        st.markdown("### Score Distributions (Top 50)")
        df_top_50 = df_results.head(50)
        
        fig_dist = px.bar(
            df_top_50,
            x="Candidate ID",
            y="Score",
            title="Composite Score Distribution across Candidates",
            labels={"Score": "Normalized Score", "Candidate ID": "Candidate"},
            color="Score",
            color_continuous_scale="Viridis"
        )
        fig_dist.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_dist, use_container_width=True)

# ----------------------------------------------------
# Tab 3: Score Breakdown
# ----------------------------------------------------
with tab3:
    if st.session_state.ranked_results is None:
        st.warning("Please upload candidate data and click 'Run Ranker 🚀' in the 'Upload & Rank' tab first.")
    else:
        st.markdown("### Detailed Score Breakdown")
        
        # Build dropdown options
        dropdown_options = []
        for idx, r in enumerate(st.session_state.ranked_results, start=1):
            cid = r["candidate_id"]
            c = st.session_state.candidates_by_id[cid]
            profile = c.get("profile") or {}
            title = profile.get("current_title") or c.get("current_title") or "N/A"
            co = profile.get("current_company") or c.get("current_company") or "N/A"
            dropdown_options.append(f"Rank {idx} — {cid} — {title} @ {co}")
            
        selected_option = st.selectbox("Select Candidate to Inspect", dropdown_options)
        
        # Extract selected rank index
        selected_rank = int(selected_option.split(" — ")[0].replace("Rank ", ""))
        selected_r = st.session_state.ranked_results[selected_rank - 1]
        selected_cid = selected_r["candidate_id"]
        selected_c = st.session_state.candidates_by_id[selected_cid]
        selected_profile = selected_c.get("profile") or {}
        selected_signals = selected_c.get("redrob_signals") or {}

        # Plotly horizontal component breakdown chart
        components_df = pd.DataFrame({
            "Metric Layer": [
                "Skills Score", "Career Score", "Experience Score",
                "Location Score", "Education Score", "Behavioral Multiplier",
                "TF-IDF Score"
            ],
            "Value": [
                selected_r["skills_score"], selected_r["career_score"], selected_r["experience_score"],
                selected_r["location_score"], selected_r["education_score"], selected_r["behavioral_multiplier"],
                selected_r["tfidf_score"]
            ]
        })
        
        fig_breakdown = px.bar(
            components_df,
            x="Value",
            y="Metric Layer",
            orientation="h",
            labels={"Value": "Component Value", "Metric Layer": "Scoring Layer"},
            title=f"Modular Breakdown for {selected_cid}",
            color="Metric Layer",
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig_breakdown.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_breakdown, use_container_width=True)

        # Profile facts cards
        st.markdown("---")
        st.markdown("### Profile highlights")
        
        c1, c2 = st.columns(2)
        
        # col 1: basic information
        c1.markdown(f"**Name (Anonymized)**: `{selected_profile.get('anonymized_name', 'N/A')}`")
        c1.markdown(f"**Headline**: {selected_profile.get('headline', 'N/A')}")
        c1.markdown(f"**Location**: {selected_profile.get('location', 'N/A')}, {selected_profile.get('country', 'N/A')}")
        c1.markdown(f"**Years of Experience**: {selected_profile.get('years_of_experience', 'N/A')} YOE")
        c1.markdown(f"**Current Title**: {selected_profile.get('current_title', 'N/A')}")
        
        skills_list = selected_c.get("skills") or []
        skills_str_list = []
        for s in skills_list[:5]:
            if isinstance(s, dict):
                skills_str_list.append(f"{s.get('name')} ({s.get('proficiency')})")
            else:
                skills_str_list.append(str(s))
        c1.markdown(f"**Top 5 Skills**: {', '.join(skills_str_list) if skills_str_list else 'None'}")

        # col 2: activity signals
        c2.markdown(f"**Open to Work Flag**: `{selected_signals.get('open_to_work_flag', 'N/A')}`")
        c2.markdown(f"**Notice Period (Days)**: {selected_signals.get('notice_period_days', 'N/A')} days")
        c2.markdown(f"**Recruiter Response Rate**: {selected_signals.get('recruiter_response_rate', 'N/A')}")
        c2.markdown(f"**Last Active Date**: {selected_signals.get('last_active_date', 'N/A')}")

        st.divider()
        # Reasoning info container
        st.info(f"**Rank {selected_rank} Reasoning Justification**:  \n{st.session_state.reasonings.get(selected_cid, '')}")

# ----------------------------------------------------
# 🏷️ Footer
# ----------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "Built for Redrob Hackathon 2026 · Team Bibhu Pradhan · CPU-only offline inference"
    "</div>",
    unsafe_allow_html=True
)
