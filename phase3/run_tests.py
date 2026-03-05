#!/usr/bin/env python3
"""
Simple test runner for Phase 3 integration testing.
Tests retrieval functionality with sample data.
"""

import sys
from pathlib import Path
import json

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import Config
except ImportError:
    # Try phase0.config
    from phase0.config import Config
from embeddings import EmbeddingModel
from vector_store import VectorStore
from doc_store import DocumentStore
from retriever import Retriever
from test_data import SAMPLE_CHUNKS, TEST_QUERIES


def setup_test_data(config):
    """Set up test data for integration testing."""
    print("Setting up test data...")

    # Initialize components
    try:
        embedding_model = EmbeddingModel(
            model_name=config.embedding_model,
            provider=config.embedding_provider,
            api_key=config.embedding_api_key
        )
    except Exception as e:
        print(f"⚠️  Embedding model setup failed: {e}")
        print("Using mock embedding model for testing...")
        # Create a simple mock that returns fixed embeddings
        class MockEmbeddingModel:
            def __init__(self):
                self.dimension = 1536
            def encode(self, texts, **kwargs):
                import numpy as np
                return np.random.rand(len(texts), self.dimension).astype(np.float32)
            def encode_single(self, text):
                import numpy as np
                return np.random.rand(self.dimension).astype(np.float32)

        embedding_model = MockEmbeddingModel()

    # Set up stores
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    vector_store = VectorStore(
        index_path=str(data_dir / "test_vector.faiss"),
        metadata_path=str(data_dir / "test_metadata.json")
    )

    doc_store = DocumentStore(str(data_dir / "test_doc.db"))

    # Populate document store
    print("Populating document store...")
    for chunk in SAMPLE_CHUNKS:
        doc_store.add_document(
            doc_id=chunk["source_id"],
            url=chunk["url"],
            fetched_at=chunk["fetched_at"]
        )
        doc_store.add_chunk(**chunk)

        # Extract typed facts
        if "AUM" in chunk["text"] and "9,102.56" in chunk["text"]:
            doc_store.add_typed_fact(
                fact_id=f"{chunk['chunk_id']}_aum",
                scheme_name="Navi AMC",
                field_name="fund_size_aum",
                field_value="9102.56",
                value_type="number",
                source_chunk_id=chunk["chunk_id"]
            )

        if "Minimum SIP" in chunk["text"]:
            # Extract SIP values
            import re
            sip_match = re.search(r'Minimum SIP:\s*INR\s*(\d+)', chunk["text"])
            if sip_match:
                sip_value = sip_match.group(1)
                scheme_name = "Navi Flexi Cap" if "flexi" in chunk["source_id"].lower() else \
                             "Navi ELSS Tax Saver" if "elss" in chunk["source_id"].lower() else \
                             "Navi Large Midcap" if "large_midcap" in chunk["source_id"].lower() else None

                if scheme_name:
                    doc_store.add_typed_fact(
                        fact_id=f"{chunk['chunk_id']}_sip",
                        scheme_name=scheme_name,
                        field_name="min_sip",
                        field_value=sip_value,
                        value_type="number",
                        source_chunk_id=chunk["chunk_id"]
                    )

        if "Lock-in Period" in chunk["text"]:
            doc_store.add_typed_fact(
                fact_id=f"{chunk['chunk_id']}_lockin",
                scheme_name="Navi ELSS Tax Saver",
                field_name="lock_in",
                field_value="3",
                value_type="number",
                source_chunk_id=chunk["chunk_id"]
            )

    # Build vector index
    print("Building vector index...")
    vector_store.create_index(dimension=embedding_model.dimension)

    texts = [chunk["text"] for chunk in SAMPLE_CHUNKS]
    embeddings = embedding_model.encode(texts)
    vector_store.add_vectors(embeddings, SAMPLE_CHUNKS)
    vector_store.save_index()

    return embedding_model, vector_store, doc_store


def run_query_test(retriever, query_data):
    """Run a single query test."""
    query = query_data["query"]
    expected_contains = query_data["expected_answer_contains"]
    expected_url = query_data["expected_url"]
    query_type = query_data["query_type"]

    print(f"\n🔍 Testing query: '{query}'")
    print(f"   Expected type: {query_type}")

    try:
        results = retriever.retrieve(query, top_k=5)

        if not results:
            print("   ❌ No results returned")
            return False

        # Check if expected content is found
        found_expected = False
        found_url = False

        for result in results:
            content = result.get("content", "").lower()
            metadata = result.get("metadata", {})

            # Check content
            if any(expected.lower() in content for expected in expected_contains):
                found_expected = True

            # Check URL in metadata
            if expected_url in str(metadata):
                found_url = True

        success = found_expected and found_url

        if success:
            print("   ✅ Test PASSED")
            print(f"   📄 Found content: {any(expected in result['content'] for result in results for expected in expected_contains)}")
            print(f"   🔗 Found URL: {found_url}")
        else:
            print("   ❌ Test FAILED")
            print(f"   📄 Expected content: {expected_contains}")
            print(f"   🔗 Expected URL: {expected_url}")
            print("   📋 Actual results:")
            for i, result in enumerate(results[:3]):
                print(f"      {i+1}. {result['content'][:100]}...")

        return success

    except Exception as e:
        print(f"   ❌ Test ERROR: {e}")
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting Phase 3 Integration Tests")
    print("=" * 50)

    try:
        config = Config()
        print("✅ Configuration loaded")
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return

    # Setup test data
    try:
        embedding_model, vector_store, doc_store = setup_test_data(config)
        retriever = Retriever(embedding_model, vector_store, doc_store)
        print("✅ Test data setup complete")
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return

    # Run query tests
    print("\n🧪 Running Query Tests")
    print("-" * 30)

    passed = 0
    total = len(TEST_QUERIES)

    for query_data in TEST_QUERIES:
        if run_query_test(retriever, query_data):
            passed += 1

    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")


def test_specific_example():
    """Test the specific example from the user."""
    print("🎯 Testing Specific Example: AUM Query")
    print("=" * 40)

    try:
        config = Config()
        embedding_model, vector_store, doc_store = setup_test_data(config)
        retriever = Retriever(embedding_model, vector_store, doc_store)

        query = "what is the AUM of Navi AMC?"
        print(f"Query: {query}")

        results = retriever.retrieve(query)

        print("\n📋 Retrieval Results:")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['type']}] {result['content']}")
            if 'metadata' in result and result['metadata']:
                metadata = result['metadata']
                if 'url' in metadata:
                    print(f"   URL: {metadata['url']}")

        # Check for expected answer
        expected_answer = "INR 9,102.56 Cr"
        expected_url = "https://groww.in/mutual-funds/amc/navi-mutual-funds"

        found_answer = any(expected_answer.replace(",", "").replace(" ", "") in result['content'].replace(",", "").replace(" ", "")
                          for result in results)
        found_url = any(expected_url in str(result.get('metadata', {})) for result in results)

        print("\n✅ Expected Answer:")
        print(f"   Content: {expected_answer}")
        print(f"   URL: {expected_url}")

        print("\n📊 Validation:")
        print(f"   Answer found: {'✅' if found_answer else '❌'}")
        print(f"   URL found: {'✅' if found_url else '❌'}")

        if found_answer and found_url:
            print("\n🎉 Example test PASSED!")
        else:
            print("\n⚠️  Example test needs improvement")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--example":
        test_specific_example()
    else:
        run_integration_tests()