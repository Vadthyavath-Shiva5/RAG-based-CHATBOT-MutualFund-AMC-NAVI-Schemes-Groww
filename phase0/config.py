"""Configuration loader for RAG Chatbot"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager"""

    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("API_DEBUG", "false").lower() == "true"

    # LLM Configuration
    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "openai")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")

    @property
    def llm_api_key(self) -> str:
        if self.llm_provider == "anthropic":
            key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        else:
            key = os.getenv("LLM_API_KEY")
        if not key:
            logger.warning("LLM_API_KEY not set in environment - using demo mode")
            return "demo-key-not-configured"
        return key

    @property
    def llm_temperature(self) -> float:
        return float(os.getenv("LLM_TEMPERATURE", "0.3"))

    # Embedding Configuration
    @property
    def embedding_provider(self) -> str:
        return os.getenv("EMBEDDING_PROVIDER", "hf")

    @property
    def embedding_model(self) -> str:
        return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    @property
    def embedding_api_key(self) -> str:
        if self.embedding_provider.lower() == "openai":
            key = os.getenv("EMBEDDING_API_KEY")
            if not key:
                raise ValueError("EMBEDDING_API_KEY not set in environment")
            return key
        return os.getenv("EMBEDDING_API_KEY", "")

    # Vector Store Configuration
    @property
    def vector_db_type(self) -> str:
        return os.getenv("VECTOR_DB_TYPE", "faiss")

    @property
    def vector_db_path(self) -> str:
        return os.getenv("VECTOR_DB_PATH", "./data/vector_store")

    # Document Store Configuration
    @property
    def doc_store_type(self) -> str:
        return os.getenv("DOC_STORE_TYPE", "sqlite")

    @property
    def doc_store_path(self) -> str:
        return os.getenv("DOC_STORE_PATH", "./data/doc_store.db")

    # API Configuration
    @property
    def api_host(self) -> str:
        return os.getenv("API_HOST", "0.0.0.0")

    @property
    def api_port(self) -> int:
        return int(os.getenv("API_PORT", "8000"))

    @property
    def cors_allow_origins(self) -> str:
        """
        Comma-separated allowlist for CORS origins.
        Use '*' for local development.
        """
        return os.getenv("CORS_ALLOW_ORIGINS", "*")

    @property
    def rate_limit_enabled(self) -> bool:
        """
        Chat endpoint rate limiting toggle.
        Defaults to true in production, false otherwise.
        """
        default = "true" if self.env.lower() == "production" else "false"
        return os.getenv("RATE_LIMIT_ENABLED", default).lower() == "true"

    @property
    def rate_limit_requests_per_minute(self) -> int:
        return int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30"))

    @property
    def rate_limit_window_seconds(self) -> int:
        return int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Paths
    @property
    def data_dir(self) -> Path:
        return Path(os.getenv("DATA_DIR", "./data"))

    @property
    def sources_yaml_path(self) -> Path:
        return Path(os.getenv("SOURCES_YAML_PATH", "./phase0/sources.yaml"))

    @property
    def cache_dir(self) -> Path:
        return Path(os.getenv("CACHE_DIR", "./data/cache"))

    # Safety Configuration
    @property
    def pii_detection_enabled(self) -> bool:
        return os.getenv("PII_DETECTION_ENABLED", "true").lower() == "true"

    @property
    def scope_classifier_enabled(self) -> bool:
        return os.getenv("SCOPE_CLASSIFIER_ENABLED", "true").lower() == "true"

    @property
    def policy_enforcer_enabled(self) -> bool:
        return os.getenv("POLICY_ENFORCER_ENABLED", "true").lower() == "true"

    # Response Configuration
    @property
    def min_citation_confidence(self) -> float:
        return float(os.getenv("MIN_CITATION_CONFIDENCE", "0.85"))

    def load_sources(self) -> Dict[str, Any]:
        """Load sources.yaml configuration"""
        with open(self.sources_yaml_path, "r") as f:
            return yaml.safe_load(f)

    def get_source_by_id(self, source_id: str) -> Dict[str, Any]:
        """Get a specific source by ID"""
        sources = self.load_sources()
        for source in sources.get("sources", []):
            if source.get("id") == source_id:
                return source
        raise ValueError(f"Source {source_id} not found")


# Global config instance
config = Config()
