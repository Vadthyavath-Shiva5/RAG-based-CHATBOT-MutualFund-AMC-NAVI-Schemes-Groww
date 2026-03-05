"""
Retrieval logic for Phase 3 indexing.
Routes queries between vector store and document store based on query type.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import numpy as np

from .embeddings import EmbeddingModel
from .vector_store import VectorStore
from .doc_store import DocumentStore

logger = logging.getLogger(__name__)


class Retriever:
    """Query routing and retrieval logic for dual-store architecture."""

    # Numeric field patterns for typed fact queries
    NUMERIC_FIELDS = {
        'nav', 'nav_value', 'expense_ratio', 'min_sip', 'min_lumpsum',
        'exit_load', 'lock_in', 'fund_size_aum', 'aum', 'ter'
    }

    # Education query keywords
    EDUCATION_KEYWORDS = {
        'what', 'how', 'explain', 'definition', 'meaning', 'about',
        'difference', 'compare', 'vs', 'versus', 'advantages', 'disadvantages'
    }

    def __init__(self, embedding_model: EmbeddingModel, vector_store: VectorStore,
                 doc_store: DocumentStore):
        """
        Initialize retriever.

        Args:
            embedding_model: Embedding model for semantic search
            vector_store: Vector store for semantic retrieval
            doc_store: Document store for structured queries
        """
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.doc_store = doc_store

    def classify_query(self, query: str) -> str:
        """
        Classify query type for routing.

        Args:
            query: User query string

        Returns:
            Query type: 'numeric', 'factual', 'educational'
        """
        query_lower = query.lower()

        # Check for numeric field queries
        for field in self.NUMERIC_FIELDS:
            if field.replace('_', ' ') in query_lower or field in query_lower:
                # Look for question patterns around numeric fields
                if any(word in query_lower for word in ['what is', 'what\'s', 'tell me', 'show me']):
                    return 'numeric'

        # Check for education queries
        if any(keyword in query_lower for keyword in self.EDUCATION_KEYWORDS):
            return 'educational'

        # Default to factual
        return 'factual'

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information for a query.

        Args:
            query: User query string
            top_k: Number of results to return

        Returns:
            List of retrieval results with metadata
        """
        query_type = self.classify_query(query)
        logger.info(f"Query classified as: {query_type}")

        if query_type == 'numeric':
            return self._retrieve_numeric(query, top_k)
        elif query_type == 'educational':
            return self._retrieve_educational(query, top_k)
        else:  # factual
            return self._retrieve_factual(query, top_k)

    def _retrieve_numeric(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Retrieve numeric facts from typed facts store, fallback to vector search.

        Args:
            query: Numeric query
            top_k: Number of results

        Returns:
            List of fact results
        """
        results = []

        # Extract field names from query
        query_fields = self._extract_numeric_fields(query)

        if query_fields:
            # Query typed facts store
            for field in query_fields:
                facts = self.doc_store.get_typed_facts(field_name=field)
                for fact in facts[:top_k]:
                    result = {
                        'type': 'typed_fact',
                        'content': f"{fact['field_name']}: {fact['field_value']}",
                        'metadata': fact,
                        'score': fact['confidence'],
                        'source': 'doc_store'
                    }
                    results.append(result)

        # If no typed facts found, fallback to vector search
        if not results:
            logger.info("No typed facts found, falling back to vector search")
            vector_results = self._vector_search(query, top_k)
            results.extend(vector_results)

        return results[:top_k]

    def _retrieve_educational(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Retrieve educational content, preferring AMFI/SEBI sources.

        Args:
            query: Educational query
            top_k: Number of results

        Returns:
            List of educational results
        """
        # Prefer AMFI/SEBI chunks for educational queries
        amfi_chunks = self.doc_store.get_chunks_by_type('narrative')
        amfi_chunks = [c for c in amfi_chunks if 'amfi' in c['document_id'].lower() or 'sebi' in c['document_id'].lower()]

        if amfi_chunks:
            # Use vector search on AMFI/SEBI chunks only
            return self._vector_search(query, top_k, filter_chunks=amfi_chunks)
        else:
            # Fallback to general vector search
            return self._vector_search(query, top_k)

    def _retrieve_factual(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Retrieve factual information using vector search.

        Args:
            query: Factual query
            top_k: Number of results

        Returns:
            List of factual results
        """
        return self._vector_search(query, top_k)

    def _vector_search(self, query: str, top_k: int,
                      filter_chunks: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            query: Query string
            top_k: Number of results
            filter_chunks: Optional chunk filter

        Returns:
            List of search results
        """
        # Encode query
        query_embedding = self.embedding_model.encode_single(query)

        # Search vector store
        search_results = self.vector_store.search(query_embedding, k=top_k)

        results = []
        for metadata, score in search_results:
            # Apply chunk filter if provided
            if filter_chunks:
                chunk_ids = {c['id'] for c in filter_chunks}
                if metadata.get('chunk_id') not in chunk_ids:
                    continue

            result = {
                'type': 'vector_result',
                'content': metadata.get('text', ''),
                'metadata': metadata,
                'score': score,
                'source': 'vector_store'
            }
            results.append(result)

        return results

    def _extract_numeric_fields(self, query: str) -> List[str]:
        """
        Extract numeric field names from query.

        Args:
            query: Query string

        Returns:
            List of field names found in query
        """
        query_lower = query.lower()
        found_fields = []

        for field in self.NUMERIC_FIELDS:
            # Check various forms
            field_forms = [
                field,
                field.replace('_', ' '),
                field.replace('_', '-')
            ]

            for form in field_forms:
                if form in query_lower:
                    found_fields.append(field)
                    break

        return list(set(found_fields))  # Remove duplicates

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval system statistics."""
        return {
            'vector_store': self.vector_store.get_stats(),
            'doc_store': self.doc_store.get_stats(),
            'embedding_model': {
                'model_name': self.embedding_model.model_name,
                'dimension': self.embedding_model.dimension
            }
        }