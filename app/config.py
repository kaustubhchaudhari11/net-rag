import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    vector_db_dir: str = os.getenv("VECTOR_DB_DIR", "./app/data/vector_db")
    top_k: int = int(os.getenv("TOP_K", "5"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "900"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_timeout_sec: int = int(os.getenv("LLM_TIMEOUT_SEC", "60"))
    # When false, omit latency breakdown and LLM token usage from /query (answer unchanged).
    include_dev_metrics: bool = os.getenv("INCLUDE_DEV_METRICS", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    hybrid_enabled: bool = os.getenv("HYBRID_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    hybrid_candidate_multiplier: int = int(os.getenv("HYBRID_CANDIDATE_MULTIPLIER", "4"))
    hybrid_dense_weight: float = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.7"))
    hybrid_keyword_weight: float = float(os.getenv("HYBRID_KEYWORD_WEIGHT", "0.3"))
    # Reciprocal Rank Fusion constant k in score 1/(k+rank); common default 60.
    hybrid_rrf_k: int = int(os.getenv("HYBRID_RRF_K", "60"))


settings = Settings()
