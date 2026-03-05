# Phase 2: Document Processing & Chunking

This phase transforms parsed documents into RAG-ready chunks optimized for retrieval-augmented generation.

## What This Phase Does

**2A) Cleaning & Structure**
- Remove navigation bars, footers, boilerplate
- Preserve headings, sections, Q&A blocks
- Convert tables to dual format: markdown (for LLM) + JSON (for direct answers)
- Maintain section context (breadcrumb paths)

**2B) Hybrid Chunking Strategy**
Four types of chunks for different retrieval patterns:

1. **Narrative Chunks** (300–800 tokens)
   - One section per chunk with stable headings
   - Example: "Minimum Investment Requirements" section
   - Includes section path, metadata

2. **FAQ Chunks** (one Q+A pair per chunk)
   - Direct question-answer format
   - Extracted from scheme pages or documentation
   - High precision for factual queries

3. **Table Row Chunks** (one row per chunk + context)
   - Scheme rows from comparison tables
   - Holding rows from portfolio tables
   - Includes table headers and summary context

4. **Typed-Fact Chunks** (small, generated)
   - Created from normalized JSON fields
   - Example: "Navi Flexi Cap: Expense Ratio 0.35% p.a."
   - Strict schema for guaranteed accuracy

## Chunk Metadata

```json
{
  "chunk_id": "link-03_chunk_001",
  "source_id": "link-03",
  "source_url": "https://groww.in/mutual-funds/navi-flexi-cap-direct-growth",
  "doc_version": "2026-03-05",
  "fetched_at": "2026-03-05T10:30:00Z",
  "chunk_type": "narrative|faq|table_row|typed_fact",
  "section_path": "Fund Details > Minimum Investments",
  "text": "The minimum SIP amount is ₹100...",
  "fields_present": ["min_sip", "nav", "expense_ratio"],
  "character_count": 524,
  "token_estimate": 128
}
```

## Key Files

- `process.py` - Main document processor orchestrator
- `lib/cleaner.py` - HTML/text cleanup, structure preservation
- `lib/chunker.py` - Chunk creation (narrative, FAQ, table rows, facts)
- `lib/table_handler.py` - Extract tables as markdown + JSON

## Running Phase 2

```bash
python phase2/process.py
```

This will:
1. Read parsed documents from `data/parsed/`
2. Clean and structure content
3. Generate hybrid chunks
4. Write chunks to `data/chunks/` as JSONL files
5. Include schema validation and metadata

## Output Structure

After Phase 2 completes:
```
data/
└── chunks/
    ├── link-01_groww_amc.jsonl         (one JSON per line = one chunk)
    ├── link-03_navi_flexi_cap.jsonl
    ├── link-12_amfi_intro_mf.jsonl
    └── ...
```

Each JSONL file contains multiple chunk records:
```jsonl
{"chunk_id": "...", "text": "...", "fields_present": [...], ...}
{"chunk_id": "...", "text": "...", "fields_present": [...], ...}
...
```

## Chunking Examples

### Narrative Chunk
```json
{
  "chunk_id": "link-03_narrative_001",
  "section_path": "Investment Details > Min Investment",
  "text": "Minimum SIP Investment: ₹100\nYou can start investing with just ₹100...",
  "chunk_type": "narrative",
  "fields_present": ["min_sip"]
}
```

### FAQ Chunk
```json
{
  "chunk_id": "link-03_faq_001",
  "text": "Q: What is the minimum SIP?\nA: The minimum SIP is ₹100 per month.",
  "chunk_type": "faq",
  "fields_present": ["min_sip"]
}
```

### Table Row Chunk
```json
{
  "chunk_id": "link-02_table_row_001",
  "text": "Scheme: Navi Flexi Cap | NAV: ₹45.32 | Exp Ratio: 0.35% | Min SIP: ₹100",
  "chunk_type": "table_row",
  "fields_present": ["nav", "expense_ratio", "min_sip"]
}
```

### Typed-Fact Chunk
```json
{
  "chunk_id": "link-03_fact_001",
  "text": "Expense Ratio: Navi Flexi Cap charges 0.35% per annum.",
  "chunk_type": "typed_fact",
  "fields_present": ["expense_ratio"],
  "confidence": 0.99
}
```

## Quality Checks

- [ ] All chunks have valid metadata
- [ ] Fields present are accurate
- [ ] Token estimates are reasonable
- [ ] Section paths preserved
- [ ] Tables are readable in markdown
- [ ] Chunk size fits within retrieval limits

## Next Step

Proceed to **Phase 3** for vector indexing and retrieval optimization.
