"""
Vector store implementation using FAISS for Phase 3 indexing.
Manages chunk embeddings with metadata for semantic retrieval.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import faiss

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for chunk embeddings and metadata."""

    def __init__(self, index_path: str, metadata_path: str):
        """
        Initialize vector store.

        Args:
            index_path: Path to save/load FAISS index
            metadata_path: Path to save/load metadata JSON
        """
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension: Optional[int] = None

    def create_index(self, dimension: int, index_type: str = "IndexFlatIP"):
        """
        Create a new FAISS index.

        Args:
            dimension: Embedding dimension
            index_type: FAISS index type (IndexFlatIP for cosine similarity)
        """
        self.dimension = dimension

        if index_type == "IndexFlatIP":
            # Inner product (cosine similarity with normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
        elif index_type == "IndexIVFFlat":
            # IVF with flat quantizer (faster for large datasets)
            nlist = min(100, max(4, int(np.sqrt(1000))))  # Rough heuristic
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        logger.info(f"Created {index_type} index with dimension {dimension}")

    def load_index(self) -> bool:
        """
        Load existing FAISS index and metadata.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.index_path.exists() or not self.metadata_path.exists():
            logger.info("Index files not found")
            return False

        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_path))

            # Load metadata
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metadata = data['metadata']
                self.dimension = data.get('dimension')

            logger.info(f"Loaded index with {len(self.metadata)} vectors")
            return True

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def save_index(self):
        """Save FAISS index and metadata to disk."""
        if self.index is None:
            raise ValueError("No index to save")

        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))

        # Save metadata
        data = {
            'metadata': self.metadata,
            'dimension': self.dimension
        }

        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved index with {len(self.metadata)} vectors")

    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """
        Add vectors and metadata to the index.

        Args:
            vectors: Embedding vectors (n_vectors, dimension)
            metadata: List of metadata dicts, one per vector
        """
        if self.index is None:
            raise ValueError("Index not initialized")

        if len(vectors) != len(metadata):
            raise ValueError("Vectors and metadata length mismatch")

        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension {vectors.shape[1]} != index dimension {self.dimension}")

        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized_vectors = vectors / norms

        # Add to FAISS index
        self.index.add(normalized_vectors.astype(np.float32))

        # Add metadata
        self.metadata.extend(metadata)

        logger.info(f"Added {len(vectors)} vectors to index")

    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding (dimension,)
            k: Number of results to return

        Returns:
            List of (metadata, similarity_score) tuples
        """
        if self.index is None:
            raise ValueError("Index not initialized")

        # Normalize query vector
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            normalized_query = query_vector
        else:
            normalized_query = query_vector / query_norm

        # Search
        query_matrix = normalized_query.reshape(1, -1).astype(np.float32)
        scores, indices = self.index.search(query_matrix, min(k, self.index.ntotal))

        # Return results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.metadata):  # Valid index
                results.append((self.metadata[idx], float(score)))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if self.index is None:
            return {"status": "not_initialized"}

        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": type(self.index).__name__
        }