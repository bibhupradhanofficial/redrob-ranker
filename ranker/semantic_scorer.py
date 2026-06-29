import logging
import numpy as np
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class SemanticScorer:
    """
    Two-stage semantic scorer:
    Stage A (all 100K): Fast TF-IDF cosine similarity between JD and candidate text.
    Stage B (top-N after Stage A): Optional lightweight sentence-transformer for
                                   semantic re-ranking (CPU, all-MiniLM-L6-v2).

    Stage A is always run. Stage B is run only on candidates that pass a configurable
    score threshold from Stage A (default: top 2000 candidates by composite score).

    TF-IDF is computed over the FULL candidate pool during fit.
    This is memory-efficient since TF-IDF matrices are sparse.
    """

    def __init__(self, use_semantic: bool = True):
        self.use_semantic = use_semantic
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english"
        )
        self.tfidf_matrix = None      # Fitted later
        self.candidate_ids = []       # Parallel list of IDs
        self.jd_vector = None
        self.semantic_model = None    # Loaded lazily
        self._semantic_embeddings = {}  # candidate_id -> embedding

        # JD text from jd_config.py
        from ranker.jd_config import JD_TEXT
        self.jd_text = JD_TEXT

    def fit(self, candidates: list[dict]):
        """
        Fit TF-IDF on full candidate pool. Call once.
        Uses DataLoader.get_candidate_text() to build corpus.
        Shows tqdm progress bar.
        """
        from ranker.data_loader import DataLoader
        corpus = []
        self.candidate_ids = []
        for c in tqdm(candidates, desc="Building TF-IDF corpus"):
            text = DataLoader.get_candidate_text(c)
            # Ensure text is not purely empty or whitespace
            if not text.strip():
                text = ""
            corpus.append(text)
            self.candidate_ids.append(c.get("candidate_id") or c.get("id") or "N/A")

        # Fit on corpus + JD together (JD as last document)
        all_texts = corpus + [self.jd_text]
        matrix = self.vectorizer.fit_transform(all_texts)
        self.tfidf_matrix = matrix[:-1]     # candidate rows
        self.jd_vector = matrix[-1]         # JD row

    def tfidf_scores(self) -> dict[str, float]:
        """
        Compute cosine similarity between JD and all candidates.
        Returns dict: candidate_id -> tfidf_score (float in [0, 1]).
        """
        if self.tfidf_matrix is None or self.jd_vector is None:
            logger.warning("TF-IDF matrix or JD vector is not fitted yet.")
            return {}

        sims = cosine_similarity(self.jd_vector, self.tfidf_matrix).flatten()
        
        scores_dict = {}
        for cid, s in zip(self.candidate_ids, sims):
            # Safe conversion and check for NaN/inf
            val = float(s)
            if np.isnan(val) or np.isinf(val):
                val = 0.0
            scores_dict[cid] = max(0.0, min(1.0, val))
            
        return scores_dict

    def load_semantic_model(self):
        """
        Lazy-load sentence-transformers model (all-MiniLM-L6-v2).
        This model is ~22MB and runs entirely on CPU.
        Only called if use_semantic=True.
        """
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2' on CPU...")
        self.semantic_model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            device="cpu"
        )
        # Pre-encode JD
        self.jd_embedding = self.semantic_model.encode(
            [self.jd_text], convert_to_numpy=True, show_progress_bar=False
        )

    def compute_semantic_scores(self, top_candidates: list[dict]) -> dict[str, float]:
        """
        Compute semantic similarity for a subset of candidates (top-N).
        Returns dict: candidate_id -> semantic_score (float in [0, 1]).
        Called only on top 1500-2000 candidates after TF-IDF pre-filter.
        """
        if not top_candidates:
            return {}

        if self.semantic_model is None:
            self.load_semantic_model()

        from ranker.data_loader import DataLoader

        texts = []
        ids = []
        for c in top_candidates:
            text = DataLoader.get_candidate_text(c)
            # Safe check for empty text
            if not text.strip():
                text = ""
            texts.append(text)
            ids.append(c.get("candidate_id") or c.get("id") or "N/A")

        # Batch encode (batch_size=64 for CPU efficiency)
        embeddings = self.semantic_model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        sims = cosine_similarity(self.jd_embedding, embeddings).flatten()
        
        scores_dict = {}
        for cid, s in zip(ids, sims):
            val = float(s)
            if np.isnan(val) or np.isinf(val):
                val = 0.0
            scores_dict[cid] = max(0.0, min(1.0, val))
            
        return scores_dict
