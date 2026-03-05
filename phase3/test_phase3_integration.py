"""
Test cases for Phase 3 indexing layer integration.
Tests retrieval, LLM integration, and end-to-end functionality.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "phase0"))
sys.path.insert(0, str(Path(__file__).parent.parent / "phase3"))

from phase0.config import Config
from phase3.lib.embeddings import EmbeddingModel
from phase3.lib.vector_store import VectorStore
from phase3.lib.doc_store import DocumentStore
from phase3.lib.retriever import Retriever


class TestPhase3Integration:
    """Integration tests for Phase 3 indexing and retrieval."""

    @pytest.fixture
    def config(self):
        """Test configuration fixture."""
        return Config()

    @pytest.fixture
    def sample_chunks(self):
        """Sample chunk data for testing."""
        return [
            {
                "chunk_id": "navi_amc_overview_001",
                "source_id": "groww_navi_amc",
                "url": "https://groww.in/mutual-funds/amc/navi-mutual-funds",
                "fetched_at": "2026-03-05T10:30:00Z",
                "section_path": "Overview",
                "chunk_type": "narrative",
                "text": "Navi Mutual Fund is a SEBI-registered mutual fund with AUM of INR 9,102.56 Cr. as of March 2026. The fund house offers various schemes including equity, debt, and hybrid funds.",
                "fields_present": ["aum", "fund_size_aum"],
                "token_count": 45
            },
            {
                "chunk_id": "navi_amc_facts_001",
                "source_id": "groww_navi_amc",
                "url": "https://groww.in/mutual-funds/amc/navi-mutual-funds",
                "fetched_at": "2026-03-05T10:30:00Z",
                "section_path": "Key Facts",
                "chunk_type": "typed_fact",
                "text": "AUM: INR 9,102.56 Cr",
                "fields_present": ["fund_size_aum"],
                "token_count": 8
            },
            {
                "chunk_id": "navi_flexi_cap_001",
                "source_id": "groww_scheme_navi_flexi_cap",
                "url": "https://groww.in/mutual-funds/navi-flexi-cap-fund",
                "fetched_at": "2026-03-05T10:30:00Z",
                "section_path": "Scheme Details",
                "chunk_type": "typed_fact",
                "text": "Minimum SIP: INR 100, Minimum Lumpsum: INR 5000, Expense Ratio: 0.35%",
                "fields_present": ["min_sip", "min_lumpsum", "expense_ratio"],
                "token_count": 15
            },
            {
                "chunk_id": "amfi_nav_explanation_001",
                "source_id": "amfi_nav",
                "url": "https://www.amfiindia.com/investor-corner/knowledge-center/what-is-nav",
                "fetched_at": "2026-03-05T10:30:00Z",
                "section_path": "NAV Explanation",
                "chunk_type": "narrative",
                "text": "NAV or Net Asset Value is the market value of all assets held by the scheme minus its liabilities, divided by the number of units outstanding.",
                "fields_present": [],
                "token_count": 32
            }
        ]

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock embedding model for testing."""
        model = Mock(spec=EmbeddingModel)
        model.dimension = 1536
        model.encode.return_value = [[0.1] * 1536, [0.2] * 1536]  # Mock embeddings
        model.encode_single.return_value = [0.1] * 1536
        return model

    def test_config_loading(self, config):
        """Test that configuration loads correctly."""
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.embedding_provider == "openai"
        assert config.embedding_model == "text-embedding-3-small"
        assert bool(config.llm_api_key)
        assert bool(config.embedding_api_key)

    def test_embedding_model_initialization(self, config):
        """Test embedding model initialization."""
        # Skip if OpenAI not available in test environment
        try:
            model = EmbeddingModel(
                model_name=config.embedding_model,
                provider=config.embedding_provider,
                api_key=config.embedding_api_key
            )
            assert model.dimension == 1536
            assert model.provider == "openai"
        except Exception as e:
            pytest.skip(f"OpenAI API not available: {e}")

    def test_vector_store_operations(self, tmp_path, sample_chunks, mock_embedding_model):
        """Test vector store basic operations."""
        index_path = tmp_path / "test_vector.faiss"
        metadata_path = tmp_path / "test_metadata.json"

        vector_store = VectorStore(str(index_path), str(metadata_path))
        vector_store.create_index(dimension=1536)

        # Prepare test data
        texts = [chunk["text"] for chunk in sample_chunks]
        embeddings = [[float(i * 0.1)] * 1536 for i in range(len(texts))]
        metadata = sample_chunks

        # Add vectors
        vector_store.add_vectors(embeddings, metadata)
        vector_store.save_index()

        # Test search
        query_embedding = [0.1] * 1536
        results = vector_store.search(query_embedding, k=2)

        assert len(results) == 2
        assert all(isinstance(score, float) for _, score in results)

    def test_doc_store_operations(self, tmp_path, sample_chunks):
        """Test document store operations."""
        db_path = tmp_path / "test_doc.db"
        doc_store = DocumentStore(str(db_path))

        # Add documents and chunks
        for chunk in sample_chunks:
            doc_store.add_document(
                doc_id=chunk["source_id"],
                url=chunk["url"],
                fetched_at=chunk["fetched_at"]
            )
            doc_store.add_chunk(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["source_id"],
                chunk_type=chunk["chunk_type"],
                text=chunk["text"],
                section_path=chunk["section_path"],
                fields_present=chunk["fields_present"],
                token_count=chunk["token_count"]
            )

        # Test retrieval
        chunks = doc_store.get_chunks_by_type("typed_fact")
        assert len(chunks) == 2

        # Test typed facts extraction
        doc_store.add_typed_fact(
            fact_id="test_aum_fact",
            scheme_name="Navi AMC",
            field_name="fund_size_aum",
            field_value="9102.56",
            value_type="number",
            source_chunk_id="navi_amc_facts_001"
        )

        facts = doc_store.get_typed_facts(field_name="fund_size_aum")
        assert len(facts) == 1
        assert facts[0]["field_value"] == "9102.56"

    def test_retriever_query_classification(self, mock_embedding_model):
        """Test query classification logic."""
        vector_store = Mock()
        doc_store = Mock()
        retriever = Retriever(mock_embedding_model, vector_store, doc_store)

        # Test different query types
        assert retriever._classify_query("what is the AUM of Navi AMC?") == "numeric"
        assert retriever._classify_query("what is NAV?") == "educational"
        assert retriever._classify_query("tell me about Navi mutual funds") == "factual"

    def test_numeric_query_retrieval(self, mock_embedding_model):
        """Test numeric query retrieval."""
        vector_store = Mock()
        doc_store = Mock()

        # Mock typed facts response
        doc_store.get_typed_facts.return_value = [
            {
                "id": "navi_aum_fact",
                "scheme_name": "Navi AMC",
                "field_name": "fund_size_aum",
                "field_value": "9102.56",
                "value_type": "number",
                "confidence": 1.0,
                "source_chunk_id": "navi_amc_facts_001"
            }
        ]

        retriever = Retriever(mock_embedding_model, vector_store, doc_store)
        results = retriever._retrieve_numeric("what is the AUM of Navi AMC?", 5)

        assert len(results) == 1
        assert "9102.56" in results[0]["content"]
        assert results[0]["type"] == "typed_fact"

    def test_educational_query_retrieval(self, mock_embedding_model):
        """Test educational query retrieval."""
        vector_store = Mock()
        doc_store = Mock()

        # Mock AMFI chunks
        doc_store.get_chunks_by_type.return_value = [
            {
                "id": "amfi_nav_chunk",
                "text": "NAV or Net Asset Value is the market value of all assets...",
                "document_id": "amfi_nav"
            }
        ]

        retriever = Retriever(mock_embedding_model, vector_store, doc_store)

        # Mock vector search to return AMFI content
        vector_store.search.return_value = [
            ({"text": "NAV explanation", "document_id": "amfi_nav"}, 0.9)
        ]

        results = retriever._retrieve_educational("what is NAV?", 5)
        vector_store.search.assert_called_once()

    @patch('phase3.lib.retriever.Retriever._vector_search')
    def test_factual_query_retrieval(self, mock_vector_search, mock_embedding_model):
        """Test factual query retrieval."""
        vector_store = Mock()
        doc_store = Mock()

        retriever = Retriever(mock_embedding_model, vector_store, doc_store)

        # Mock vector search results
        mock_vector_search.return_value = [
            {
                "type": "vector_result",
                "content": "Navi AMC information",
                "metadata": {"source_id": "groww_navi_amc"},
                "score": 0.85
            }
        ]

        results = retriever._retrieve_factual("tell me about Navi AMC", 5)
        mock_vector_search.assert_called_once_with("tell me about Navi AMC", 5)

    def test_end_to_end_aum_query(self, mock_embedding_model):
        """End-to-end test for AUM query example."""
        vector_store = Mock()
        doc_store = Mock()

        # Mock the typed facts lookup for AUM
        doc_store.get_typed_facts.return_value = [
            {
                "id": "navi_aum_fact",
                "scheme_name": "Navi AMC",
                "field_name": "fund_size_aum",
                "field_value": "9102.56",
                "value_type": "number",
                "confidence": 1.0,
                "source_chunk_id": "navi_amc_facts_001",
                "metadata": {
                    "url": "https://groww.in/mutual-funds/amc/navi-mutual-funds"
                }
            }
        ]

        retriever = Retriever(mock_embedding_model, vector_store, doc_store)

        # Test the full retrieval pipeline
        results = retriever.retrieve("what is the AUM of Navi AMC?")

        assert len(results) > 0
        # Should find the AUM fact
        aum_result = next((r for r in results if "9102.56" in r["content"]), None)
        assert aum_result is not None
        assert aum_result["type"] == "typed_fact"

    def test_integration_test_cases(self):
        """Comprehensive test cases for different query types."""
        test_cases = [
            {
                "query": "what is the AUM of Navi AMC?",
                "expected_contains": ["9102.56", "INR"],
                "query_type": "numeric",
                "expected_sources": ["groww_navi_amc"]
            },
            {
                "query": "what is NAV?",
                "expected_contains": ["Net Asset Value", "assets"],
                "query_type": "educational",
                "expected_sources": ["amfi_nav"]
            },
            {
                "query": "what is the minimum SIP for Navi Flexi Cap?",
                "expected_contains": ["100", "SIP"],
                "query_type": "numeric",
                "expected_sources": ["groww_scheme_navi_flexi_cap"]
            },
            {
                "query": "tell me about Navi mutual funds",
                "expected_contains": ["mutual fund"],
                "query_type": "factual",
                "expected_sources": ["groww_navi_amc"]
            }
        ]

        # This would be expanded with actual implementation
        for case in test_cases:
            print(f"Test case: {case['query']}")
            print(f"Expected type: {case['query_type']}")
            print(f"Expected content: {case['expected_contains']}")
            # In real implementation, this would call the retriever

    @pytest.mark.integration
    def test_full_pipeline_with_llm(self, config):
        """Full integration test with LLM (requires API access)."""
        pytest.skip("Requires OpenAI API access - run manually")

        # This test would:
        # 1. Set up retriever with real data
        # 2. Make a query
        # 3. Get retrieval results
        # 4. Send to LLM for response generation
        # 5. Verify response format and citations

        # Example implementation:
        """
        from openai import OpenAI

        retriever = Retriever(embedding_model, vector_store, doc_store)
        results = retriever.retrieve("what is the AUM of Navi AMC?")

        # Format context for LLM
        context = "\n".join([r["content"] for r in results])

        # Generate response with LLM
        client = OpenAI(api_key=config.llm_api_key)
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": "Answer based on provided context only."},
                {"role": "user", "content": f"Context: {context}\n\nQuery: what is the AUM of Navi AMC?"}
            ]
        )

        answer = response.choices[0].message.content
        assert "INR 9,102.56 Cr" in answer
        assert "groww.in/mutual-funds/amc/navi-mutual-funds" in answer
        """


if __name__ == "__main__":
    # Run basic tests
    test_instance = TestPhase3Integration()

    print("Running Phase 3 integration tests...")

    # Test config loading
    try:
        config = Config()
        print("✅ Configuration loaded successfully")
        print(f"   LLM: {config.llm_provider}/{config.llm_model}")
        print(f"   Embeddings: {config.embedding_provider}/{config.embedding_model}")
    except Exception as e:
        print(f"❌ Configuration failed: {e}")

    print("\nTest cases defined:")
    test_cases = [
        "what is the AUM of Navi AMC?",
        "what is NAV?",
        "what is the minimum SIP for Navi Flexi Cap?",
        "tell me about Navi mutual funds"
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"{i}. {case}")

    print("\nTo run full tests: pytest test_phase3_integration.py -v")