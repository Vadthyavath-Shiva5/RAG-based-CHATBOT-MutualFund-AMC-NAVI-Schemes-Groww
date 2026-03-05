"""
Phase 2 Implementation Guide and API Reference
"""

# Phase 2: Document Processing & Chunking Implementation
# ========================================================

"""
OVERVIEW
--------
Phase 2 transforms parsed documents from Phase 1 into RAG-ready chunks.
It implements a hybrid chunking strategy with 4 chunk types optimized for different retrieval patterns.

ARCHITECTURE
-----------

Input (from Phase 1):
  └─ data/parsed/
      ├─ link-01_groww_amc/
      │   ├─ document.json (structured content)
      │   ├─ text.txt (extracted text)
      │   └─ meta.json (metadata)
      └─ ...

Processing Pipeline:
  1. Load parsed documents
  2. Clean & parse structure (DocumentCleaner)
  3. Build hybrid chunks (ChunkBuilder)
  4. Extract table chunks (TableHandler)
  5. Validate chunks (ChunkValidator)
  6. Save as JSONL

Output (for Phase 3):
  └─ data/chunks/
      ├─ link-01_groww_amc.jsonl
      ├─ link-03_navi_flexi_cap.jsonl
      └─ ...

CORE COMPONENTS
---------------

1. DocumentCleaner (lib/cleaner.py)
   - Removes boilerplate (nav, footers, ads)
   - Preserves section structure with headings
   - Extracts FAQ pairs
   - Parses document into hierarchical sections

2. ChunkBuilder (lib/chunker.py)
   - Creates 4 chunk types:
     a) Narrative: 300-800 tokens, one section per chunk
     b) FAQ: one Q&A pair per chunk
     c) Typed-fact: small, high-precision facts
     d) Table rows: one row per chunk (if applicable)
   - Detects fields present in each chunk
   - Estimates token counts
   - Generates unique chunk IDs

3. TableHandler (lib/table_handler.py)
   - Converts tables to dual format:
     - Markdown: for LLM readability
     - JSON: for direct structured answers
   - Detects scheme comparison tables
   - Creates either row-level or table-level chunks

4. Utilities (lib/util.py)
   - TokenEstimator: estimate token counts
   - TextCleaner: normalize text
   - FieldExtractor: extract typed fields
   - SectionParser: build section hierarchies
   - ChunkValidator: validate chunk quality

CHUNK STRUCTURE
---------------

All chunks follow this schema:

{
  "chunk_id": "link-03_chunk_001",                    # Unique identifier
  "source_id": "link-03",                             # Source link ID
  "source_url": "https://groww.in/...",              # Full source URL
  "doc_version": "2026-03-05T10:30:00Z",             # When document was fetched
  "fetched_at": "2026-03-05T10:30:00Z",              # Fetch timestamp
  "chunk_type": "narrative|faq|typed_fact|table_row", # Chunk type
  "section_path": "Fund Details / Minimum Investments", # Breadcrumb path
  "text": "The minimum SIP amount is ₹100...",        # Chunk text (for LLM)
  "fields_present": ["min_sip", "expense_ratio"],    # Detected typed fields
  "character_count": 524,                            # Text length
  "token_estimate": 128,                             # Estimated tokens
  
  // Optional fields:
  "json_data": {...},                                // For table chunks
  "confidence": 0.95                                 // For typed-fact chunks
}

USAGE
-----

1. Run full processing pipeline:
   python phase2/process.py

2. Process specific source:
   python phase2/process.py --source link-03_navi_flexi_cap

3. With verification:
   python phase2/process.py --verify

4. Run examples:
   python phase2/examples.py

5. Programmatic usage:

   from phase2.process import DocumentProcessor
   
   processor = DocumentProcessor()
   result = processor.process_source(Path("data/parsed/link-03_navi_flexi_cap"))
   print(f"Generated {result['chunk_count']} chunks")

TYPED FIELD DETECTION
---------------------

Chunks automatically detect which typed fields are present:

- nav: NAV, price, net asset value
- expense_ratio: expense ratio, TER, costs
- min_sip: minimum SIP, min SIP
- min_lumpsum: minimum lumpsum, min lumpsum
- exit_load: exit load, redemption fee
- lock_in: lock-in, lock in, locked for
- risk_label: risk (low/medium/high), volatility
- aum: AUM, fund size, assets under management
- holdings: holdings, portfolio
- performance: returns, performance, gain

CHUNK TYPES IN DETAIL
---------------------

1. NARRATIVE CHUNKS (300-800 tokens)
   
   Use case: Provide context for educational queries
   Example: "Explain what is exit load"
   
   Structure:
   - One section per chunk
   - Includes heading as anchor
   - Preserves context (section path)
   - ~300-800 tokens (good for LLM context window)

2. FAQ CHUNKS (variable tokens)
   
   Use case: Direct Q&A matching
   Example: "Q: What is NAV? A: ..."
   
   Structure:
   - One question-answer pair per chunk
   - High precision for factual queries
   - Natural language pattern
   - Typically <200 tokens

3. TYPED-FACT CHUNKS (small)
   
   Use case: Direct fact lookup without LLM generation
   Example: "Navi Flexi Cap: Expense Ratio 0.35%"
   
   Structure:
   - Generated from extracted fields
   - Guaranteed accuracy
   - Small size (10-50 tokens)
   - Includes confidence score

4. TABLE ROW CHUNKS (variable tokens)
   
   Use case: Scheme comparison without generation
   Example: "Scheme: Navi Flexi Cap | NAV: 45.32 | Exp: 0.35%"
   
   Structure:
   - One row per chunk (for scheme tables)
   - Includes table headers
   - Markdown + JSON formats
   - Context from caption

EXAMPLE OUTPUT
--------------

Input document: Navi Flexi Cap scheme page

Output chunks:
1. narrative: "Overview of Navi Flexi Cap" (500 tokens)
2. narrative: "Key Information section" (400 tokens)
3. narrative: "Exit Load policy" (300 tokens)
4. faq: "Q: What is NAV?" (100 tokens)
5. faq: "Q: Can I redeem anytime?" (150 tokens)
6. typed_fact: "Expense Ratio: 0.35%" (10 tokens)
7. typed_fact: "Min SIP: ₹100" (8 tokens)
8. table_row: "Scheme comparison row" (200 tokens)

VALIDATION RULES
-----------------

Chunks are validated for:
✓ Required fields present
✓ Chunk ID format is valid
✓ Text length reasonable (10-5000 tokens)
✓ Source URL valid
✓ Timestamp present and ISO format
✓ Fields_present array not empty
✓ No missing metadata

Invalid chunks are logged and skipped with error details.

PERFORMANCE NOTES
-----------------

- Processing ~500 parsed documents: ~2-3 minutes
- Average chunks per source: 10-50 (varies by size)
- Total expected chunks: 500-2000 across all sources
- Memory usage: ~500MB-1GB (during processing)
- Output file size: ~100-200MB JSONL

TESTING & DEBUGGING
-------------------

Run examples to verify setup:
  python phase2/examples.py

Example 1: Basic Document Processing
  Shows document cleaning and chunking flow

Example 2: Field Extraction
  Demonstrates typed field detection

Example 3: Token Estimation
  Shows token counting accuracy

Example 4: Table Handling
  Displays table extraction

Example 5: Text Cleaning
  Shows text normalization

INTEGRATION WITH OTHER PHASES
------------------------------

← Phase 1: Provides parsed documents in data/parsed/
→ Phase 3: Consumes chunks from data/chunks/ to build indexes

COMMON ISSUES & SOLUTIONS
--------------------------

Issue: "No chunks generated"
Solution: Verify Phase 1 created data/parsed/ with documents

Issue: "Token estimate seems wrong"
Solution: Token estimation is approximate (rough: 1 token ≈ 4 chars)

Issue: "Fields not detected"
Solution: Add more field patterns in FieldExtractor.FIELD_PATTERNS

Issue: "Tables not extracted"
Solution: Verify table data is in document["tables"] from Phase 1

NEXT STEPS
----------

After Phase 2:
1. Verify chunks in data/chunks/*.jsonl
2. Review chunk statistics
3. Run Phase 3 to build indexes
4. Test retrieval with Phase 4 API
"""
