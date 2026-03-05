"""
Main indexing orchestrator for Phase 3.
Builds and manages dual-store search infrastructure.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add phase0 to path for config
sys.path.insert(0, str(Path(__file__).parent.parent / "phase0"))

try:
    from lib.config import Config
except ImportError:
    # Fallback if config not available
    class Config:
        def __init__(self):
            self.data_dir = Path("data")
            self.phase3_dir = Path("phase3")

from lib.embeddings import EmbeddingModel
from lib.vector_store import VectorStore
from lib.doc_store import DocumentStore

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Main indexing orchestrator for Phase 3."""

    def __init__(self, config: Config):
        """
        Initialize index builder.

        Args:
            config: Configuration object
        """
        self.config = config
        self.data_dir = config.data_dir
        self.phase3_dir = config.phase3_dir

        # Initialize components with config
        embedding_provider = getattr(config, 'embedding_provider', 'hf')
        embedding_api_key = getattr(config, 'embedding_api_key', None)

        self.embedding_model = EmbeddingModel(
            model_name=config.embedding_model,
            provider=embedding_provider,
            api_key=embedding_api_key
        )
        self.vector_store = VectorStore(
            index_path=self.phase3_dir / "vector_store.faiss",
            metadata_path=self.phase3_dir / "vector_metadata.json"
        )
        self.doc_store = DocumentStore(
            db_path=self.phase3_dir / "doc_store.db"
        )

    def setup_doc_store(self):
        """Initialize document store schema."""
        logger.info("Document store schema already initialized in constructor")
        logger.info("Document store ready")

    def load_chunks_from_phase2(self) -> List[Dict[str, Any]]:
        """
        Load processed chunks from Phase 2 output.

        Returns:
            List of chunk dictionaries
        """
        chunks_dir = self.data_dir / "chunks"
        all_chunks = []

        if not chunks_dir.exists():
            logger.warning(f"Chunks directory not found: {chunks_dir}")
            return all_chunks

        # Load chunks from all source directories
        for source_dir in chunks_dir.iterdir():
            if source_dir.is_dir():
                chunks_file = source_dir / "chunks.jsonl"
                if chunks_file.exists():
                    logger.info(f"Loading chunks from: {chunks_file}")
                    with open(chunks_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                chunk = json.loads(line)
                                all_chunks.append(chunk)

        logger.info(f"Loaded {len(all_chunks)} chunks from Phase 2")
        return all_chunks

    def embed_chunks(self):
        """Generate embeddings for all chunks and build vector index."""
        # Load chunks
        chunks = self.load_chunks_from_phase2()
        if not chunks:
            logger.error("No chunks found from Phase 2")
            return

        # Prepare texts and metadata for embedding
        texts = []
        metadata = []

        for chunk in chunks:
            text = chunk.get('text', '').strip()
            if text:
                texts.append(text)
                metadata.append({
                    'chunk_id': chunk.get('chunk_id', chunk.get('id', '')),
                    'source_id': chunk.get('source_id', ''),
                    'url': chunk.get('url', ''),
                    'fetched_at': chunk.get('fetched_at', ''),
                    'section_path': chunk.get('section_path', ''),
                    'chunk_type': chunk.get('chunk_type', ''),
                    'fields_present': chunk.get('fields_present', []),
                    'text': text  # Store text in metadata for retrieval
                })

        if not texts:
            logger.error("No valid texts found in chunks")
            return

        logger.info(f"Generating embeddings for {len(texts)} chunks")

        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, batch_size=32)

        # Create or load vector index
        if not self.vector_store.load_index():
            self.vector_store.create_index(dimension=self.embedding_model.dimension)

        # Add to vector store
        self.vector_store.add_vectors(embeddings, metadata)

        # Save index
        self.vector_store.save_index()

        logger.info("Vector index built and saved")

    def populate_doc_store(self):
        """Populate document store with chunks and extract typed facts."""
        chunks = self.load_chunks_from_phase2()

        for chunk in chunks:
            # Add document if not exists
            doc_id = chunk.get('source_id', '')
            if doc_id:
                self.doc_store.add_document(
                    doc_id=doc_id,
                    url=chunk.get('url', ''),
                    fetched_at=chunk.get('fetched_at', ''),
                    source_type='processed_chunk'
                )

            # Add chunk
            chunk_id = chunk.get('chunk_id', chunk.get('id', ''))
            if chunk_id:
                self.doc_store.add_chunk(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    chunk_type=chunk.get('chunk_type', 'unknown'),
                    text=chunk.get('text', ''),
                    section_path=chunk.get('section_path', ''),
                    fields_present=chunk.get('fields_present', []),
                    token_count=chunk.get('token_count')
                )

            # Extract and add typed facts
            self._extract_typed_facts(chunk)

        logger.info("Document store populated")

    def _extract_typed_facts(self, chunk: Dict[str, Any]):
        """Extract typed facts from chunk and add to document store."""
        fields_present = chunk.get('fields_present', [])
        chunk_id = chunk.get('chunk_id', chunk.get('id', ''))

        # Simple field extraction - in production this would be more sophisticated
        for field in fields_present:
            if field in ['nav_value', 'expense_ratio', 'min_sip', 'min_lumpsum', 'fund_size_aum']:
                # Try to extract numeric values from text
                import re
                text = chunk.get('text', '')

                if field == 'nav_value':
                    # Look for NAV patterns
                    nav_match = re.search(r'NAV[:\s]+(?:Rs\.?\s*)?(\d+\.?\d*)', text, re.IGNORECASE)
                    if nav_match:
                        value = float(nav_match.group(1))
                        self._add_typed_fact(chunk_id, field, value, 'number')

                elif field == 'expense_ratio':
                    # Look for expense ratio patterns
                    er_match = re.search(r'expense ratio[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
                    if er_match:
                        value = float(er_match.group(1))
                        self._add_typed_fact(chunk_id, field, value, 'number')

                elif field in ['min_sip', 'min_lumpsum']:
                    # Look for minimum investment patterns
                    inv_match = re.search(rf'{field.replace("_", " ")}[:\s]+(?:Rs\.?\s*)?(\d+)', text, re.IGNORECASE)
                    if inv_match:
                        value = int(inv_match.group(1))
                        self._add_typed_fact(chunk_id, field, value, 'number')

                elif field == 'fund_size_aum':
                    # Look for AUM patterns
                    aum_match = re.search(r'AUM[:\s]+(?:Rs\.?\s*)?(\d+(?:\.\d+)?)\s*(crore|cr)', text, re.IGNORECASE)
                    if aum_match:
                        value = float(aum_match.group(1))
                        if aum_match.group(2).lower() in ['crore', 'cr']:
                            value *= 10000000  # Convert crore to rupees
                        self._add_typed_fact(chunk_id, field, value, 'number')

    def _add_typed_fact(self, chunk_id: str, field_name: str, value: Any, value_type: str):
        """Add a typed fact to the document store."""
        fact_id = f"{chunk_id}_{field_name}"

        self.doc_store.add_typed_fact(
            fact_id=fact_id,
            scheme_name=None,  # Would be extracted from chunk context
            field_name=field_name,
            field_value=value,
            value_type=value_type,
            source_chunk_id=chunk_id
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        return {
            'embedding_model': {
                'model_name': self.embedding_model.model_name,
                'dimension': self.embedding_model.dimension
            },
            'vector_store': self.vector_store.get_stats(),
            'doc_store': self.doc_store.get_stats()
        }


def main():
    """Main entry point for indexing operations."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Phase 3 Indexing Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["setup_doc_store", "embed_chunks", "populate_doc_store", "stats"],
        required=True,
        help="Indexing operation to perform"
    )

    args = parser.parse_args()

    # Initialize config
    try:
        config = Config()
    except:
        # Fallback config
        config = Config()

    # Initialize index builder
    builder = IndexBuilder(config)

    # Execute requested operation
    if args.mode == "setup_doc_store":
        builder.setup_doc_store()
        print("Document store setup complete")

    elif args.mode == "embed_chunks":
        builder.embed_chunks()
        print("Chunk embedding complete")

    elif args.mode == "populate_doc_store":
        builder.populate_doc_store()
        print("Document store population complete")

    elif args.mode == "stats":
        stats = builder.get_stats()
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()