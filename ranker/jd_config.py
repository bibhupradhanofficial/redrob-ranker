JD_REQUIRED_SKILLS = [
    "embeddings", "sentence-transformers", "vector database", "pinecone", "weaviate",
    "qdrant", "milvus", "faiss", "opensearch", "elasticsearch", "dense retrieval",
    "hybrid search", "semantic search", "retrieval", "ranking", "nlp", "information retrieval",
    "python", "evaluation", "ndcg", "mrr", "map", "a/b testing", "recommendation system",
    "search", "LLM", "language model", "transformers", "fine-tuning", "RAG",
    "retrieval-augmented generation", "pytorch", "tensorflow", "applied ML", "machine learning"
]

JD_NICE_TO_HAVE_SKILLS = [
    "lora", "qlora", "peft", "learning to rank", "xgboost", "hr tech", "recruiting",
    "marketplace", "distributed systems", "inference optimization", "open source",
    "BM25", "sparse retrieval", "re-ranking", "cross-encoder", "bi-encoder"
]

JD_DISQUALIFYING_SIGNALS = {
    "consulting_companies": [
        "TCS", "Tata Consultancy", "Infosys", "Wipro", "Accenture", "Cognizant",
        "Capgemini", "HCL Technologies", "Hexaware", "Mphasis", "Tech Mahindra",
        "Mindtree", "L&T Infotech", "LTIMindtree"
    ],
    "non_ai_titles": [
        "HR Manager", "Marketing Manager", "Content Writer", "Graphic Designer",
        "Operations Manager", "Business Analyst", "Project Manager", "Sales Manager",
        "Finance Analyst", "Recruiter", "Data Entry", "Admin"
    ],
    "pure_research_keywords": [
        "research scientist", "research engineer", "academic", "PhD researcher",
        "postdoc", "research intern", "university research"
    ]
}

JD_PREFERRED_LOCATIONS = [
    "Pune", "Noida", "Delhi", "NCR", "Gurugram", "Gurgaon", "Hyderabad",
    "Mumbai", "Bangalore", "Bengaluru", "Chennai"
]

JD_EXP_RANGE = (5, 9)
JD_EXP_SOFT_MIN = 4.0
JD_EXP_SOFT_MAX = 10.0

JD_TEXT = """
We are looking for a Senior AI Engineer to join the Founding Team at Redrob AI (Pune/Noida, India, Hybrid).
The ideal candidate has 5-9 years of experience in applied ML, building and evaluating search, recommendation, and RAG systems.
You will design and implement embeddings-based retrieval, hybrid search, and dense retrieval pipelines.
Proficiency with Python, PyTorch, TensorFlow, and sentence-transformers is required.
Hands-on experience with vector databases (Pinecone, Weaviate, Qdrant, Milvus, Faiss), Elasticsearch, or OpenSearch is critical.
You will fine-tune transformers and LLMs using PEFT techniques like LoRA and QLoRA, and build learning-to-rank systems.
A strong background in information retrieval, dense/sparse retrieval (BM25), cross-encoders, bi-encoders, and evaluation metrics (NDCG, MAP, MRR) is expected.
Experience with distributed systems, inference optimization, A/B testing, and open-source contributions is a major plus.
"""
