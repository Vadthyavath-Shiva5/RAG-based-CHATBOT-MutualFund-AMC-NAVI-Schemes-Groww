"""
Phase 2 Example: Demonstrate document processing and chunking
"""

import json
from pathlib import Path
from phase2.lib.cleaner import DocumentCleaner
from phase2.lib.chunker import ChunkBuilder
from phase2.lib.table_handler import TableHandler
from phase2.lib.util import TokenEstimator, TextCleaner, FieldExtractor


# Example 1: Basic document processing
def example_basic_processing():
    """Example of basic document cleaning and chunking"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Document Processing")
    print("="*60)

    # Sample document
    sample_document = {
        "source_id": "example_source",
        "url": "https://example.com",
        "fetched_at": "2026-03-05T10:30:00Z",
        "raw_text": """
Navi Flexi Cap Fund
==================

Overview
--------
Navi Flexi Cap is a dynamic equity fund that invests across market capitalizations.

Key Information
---------------
- Minimum SIP: ₹100
- Minimum Lumpsum: ₹5000
- Expense Ratio: 0.35%
- NAV: ₹45.32 (as of 2026-03-05)

Exit Load
---------
The exit load is 0% if units are held for more than 1 year from the date of purchase.

FAQs
----
Q: What is NAV?
A: NAV stands for Net Asset Value. It is the price per unit of the fund.

Q: Can I redeem anytime?
A: Yes, you can redeem anytime, but there may be exit loads depending on holding period.
"""
    }

    # Process document
    cleaner = DocumentCleaner()
    cleaned = cleaner.clean(sample_document)

    print("\nCleaned document sections:")
    for i, section in enumerate(cleaned["content"]):
        print(f"  {i+1}. {section.get('heading', 'Untitled')}")

    # Build chunks
    chunk_builder = ChunkBuilder()
    chunks = chunk_builder.build_chunks(
        source_id="example_source",
        document=cleaned,
        metadata={"url": "https://example.com", "fetched_at": "2026-03-05"}
    )

    print(f"\nGenerated {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"  - {chunk['chunk_id']}: {chunk['chunk_type']} ({chunk['token_estimate']} tokens)")
        print(f"    Fields: {', '.join(chunk['fields_present'])}")


# Example 2: Field extraction
def example_field_extraction():
    """Example of extracting typed fields from text"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Field Extraction")
    print("="*60)

    sample_text = """
    Navi Flexi Cap Fund - Key Details
    Minimum SIP: ₹100 per month
    Minimum Lumpsum: ₹5000
    Expense Ratio: 0.35% per annum
    Current NAV: ₹45.32
    Fund Size (AUM): ₹1,250 Crore
    Exit Load: 0% if held > 1 year
    Lock-in: None (except ELSS)
    Risk Rating: High
    """

    fields = FieldExtractor.extract_fields(sample_text)

    print("\nExtracted fields:")
    for field_name, field_data in fields.items():
        print(f"  {field_name}: {field_data}")


# Example 3: Token estimation
def example_token_estimation():
    """Example of token counting"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Token Estimation")
    print("="*60)

    text = """
    Navi Flexi Cap is a dynamic equity mutual fund that provides investors
    with exposure to companies across different market capitalizations.
    The fund aims to generate long-term capital growth by investing in
    carefully selected quality companies.
    """

    tokens = TokenEstimator.estimate_tokens(text)
    words = TokenEstimator.word_count(text)
    sentences = TokenEstimator.sentence_count(text)

    print(f"\nText Analysis:")
    print(f"  Characters: {len(text)}")
    print(f"  Words: {words}")
    print(f"  Sentences: {sentences}")
    print(f"  Estimated Tokens: {tokens}")
    print(f"  Chars per Token: {len(text) / tokens:.1f}")


# Example 4: Table handling
def example_table_handling():
    """Example of table extraction"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Table Handling")
    print("="*60)

    sample_table = {
        "caption": "Navi Schemes Comparison",
        "headers": ["Scheme Name", "NAV", "Expense Ratio", "Min SIP", "Risk"],
        "rows": [
            ["Navi Flexi Cap", "₹45.32", "0.35%", "₹100", "High"],
            ["Navi Large & Midcap", "₹38.15", "0.38%", "₹100", "High"],
            ["Navi ELSS Nifty 50", "₹52.48", "0.25%", "₹100", "Medium"],
        ]
    }

    table_handler = TableHandler()
    chunks = table_handler.extract_table_chunks(
        source_id="example_schemes",
        tables=[sample_table],
        metadata={"url": "https://example.com", "fetched_at": "2026-03-05"}
    )

    print(f"\nGenerated {len(chunks)} table chunks:")
    for chunk in chunks:
        print(f"\n  Chunk ID: {chunk['chunk_id']}")
        print(f"  Type: {chunk['chunk_type']}")
        print(f"  Fields: {chunk['fields_present']}")
        print(f"  Text preview:\n{chunk['text'][:200]}...")


# Example 5: Text cleaning
def example_text_cleaning():
    """Example of text cleaning operations"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Text Cleaning")
    print("="*60)

    messy_text = """
    Check   out   https://groww.in    for  more     info!
    Contact: support@example.com
    Price: ₹   45,000
    Special chars: @#$%^&*()
    """

    print("Original text:")
    print(f"  {repr(messy_text)}")

    cleaned = TextCleaner.remove_extra_whitespace(messy_text)
    print("\nAfter whitespace cleanup:")
    print(f"  {repr(cleaned)}")

    urls = TextCleaner.extract_urls(messy_text)
    print(f"\nExtracted URLs: {urls}")

    emails = TextCleaner.extract_emails(messy_text)
    print(f"Extracted emails: {emails}")

    numbers = TextCleaner.extract_numbers(messy_text)
    print(f"Extracted numbers: {numbers}")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("PHASE 2: DOCUMENT PROCESSING & CHUNKING EXAMPLES")
    print("="*60)

    example_basic_processing()
    example_field_extraction()
    example_token_estimation()
    example_table_handling()
    example_text_cleaning()

    print("\n" + "="*60)
    print("✓ All examples completed")
    print("="*60)


if __name__ == "__main__":
    main()
