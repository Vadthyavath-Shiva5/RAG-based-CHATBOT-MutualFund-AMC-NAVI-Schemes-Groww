"""
Embedding model wrapper for Phase 3 indexing.
Provides unified interface for different embedding providers.
"""

import logging
from typing import List, Optional
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

# Import OpenAI for API-based embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for embedding models (SentenceTransformers or OpenAI)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", provider: str = "hf",
                 api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        Initialize embedding model.

        Args:
            model_name: Model name (HuggingFace or OpenAI)
            provider: 'hf' for HuggingFace/SentenceTransformers, 'openai' for OpenAI API
            api_key: API key for OpenAI (required if provider='openai')
            cache_dir: Directory to cache models
        """
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_key = api_key
        self.cache_dir = Path(cache_dir) if cache_dir else None

        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed. Install with: pip install openai")
            if not self.api_key:
                raise ValueError("API key required for OpenAI embeddings")
            self.client = OpenAI(api_key=self.api_key)
            self.dimension = 1536  # OpenAI text-embedding-3-small dimension
            logger.info(f"Initialized OpenAI embeddings: {model_name}")

        elif self.provider == "hf":
            logger.info(f"Loading HuggingFace model: {model_name}")
            self.model = SentenceTransformer(model_name, cache_folder=str(self.cache_dir) if self.cache_dir else None)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'hf' or 'openai'")

    def encode(self, texts: List[str], batch_size: int = 32, show_progress_bar: bool = True) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding (HF only)
            show_progress_bar: Whether to show progress bar (HF only)

        Returns:
            Numpy array of embeddings (n_texts, embedding_dim)
        """
        logger.info(f"Encoding {len(texts)} texts with {self.provider} provider")

        if self.provider == "openai":
            return self._encode_openai(texts)
        else:  # HuggingFace
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                convert_to_numpy=True
            )
            logger.info(f"Encoding complete. Shape: {embeddings.shape}")
            return embeddings

    def _encode_openai(self, texts: List[str]) -> np.ndarray:
        """Encode texts using OpenAI API."""
        embeddings = []

        # OpenAI has a limit on batch size, so we'll process in chunks if needed
        batch_size = 100  # OpenAI allows up to 2048 inputs per request, but we'll be conservative

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = self.client.embeddings.create(
                input=batch,
                model=self.model_name
            )

            batch_embeddings = [data.embedding for data in response.data]
            embeddings.extend(batch_embeddings)

        embeddings_array = np.array(embeddings)
        logger.info(f"OpenAI encoding complete. Shape: {embeddings_array.shape}")
        return embeddings_array

    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text string.

        Args:
            text: Text to encode

        Returns:
            Embedding vector as numpy array
        """
        return self.encode([text])[0]

    def similarity(self, query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding (1, dim)
            doc_embeddings: Document embeddings (n_docs, dim)

        Returns:
            Similarity scores (n_docs,)
        """
        # Normalize embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)

        # Cosine similarity
        similarities = np.dot(doc_norms, query_norm.T).flatten()
        return similarities