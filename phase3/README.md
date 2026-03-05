# Phase 3: Indexing Layer (Vector + Structured Store)

This phase builds dual-store search infrastructure: vector embeddings for semantic retrieval and a structured store for typed facts.

## What This Phase Does

**3A) Two-Store Architecture**
1. **Document Store** (Ground Truth)
   - Stores canonical docs, chunks, typed facts
   - Source: filesystem/SQLite (local) → Postgres (production)
   - Enables exact lookups and fact verification

2. **Vector Store** (Semantic Retrieval)
   - Stores chunk embeddings with metadata
   - Source: FAISS (local) → Chroma/Pinecone (production)
   - Powers semantic search "what is similar?"

**3B) Retrieval Routing**
Different query types use different strategies:
- **Numeric queries** (min SIP, TER, exit load): typed facts store → fast, precise
- **Factual queries** (what is NAV): vector + document store → semantic + contextual
- **Educational queries** (how MF works): prefer AMFI/SEBI chunks → authoritative

## Key Files

- `index.py` - Main indexing orchestrator
- `lib/embeddings.py` - Embedding model wrapper (OpenAI, HuggingFace)
- `lib/vector_store.py` - FAISS/Chroma management
- `lib/doc_store.py` - SQLite document storage
- `lib/retriever.py` - Query routing logic

## Building Indexes

### 1. Start Document Store (SQLite)

```bash
python phase3/index.py --mode setup_doc_store
```

Creates schema:
- `documents` table (canonical docs)
- `chunks` table (chunk records)
- `typed_facts` table (normalized facts)
- `evidence_spans` table (fact → source mappings)

### 2. Generate Embeddings

```bash
python phase3/index.py --mode embed_chunks
```

For each chunk in `data/chunks/*.jsonl`:
1. Load chunk text
2. Generate embedding (OpenAI text-embedding-3-small by default)
3. Store in vector DB
4. Link to document store

### 3. Index Typed Facts

```bash
python phase3/index.py --mode index_facts
```

For each chunk with `fields_present`:
1. Extract typed fields (min_sip, expense_ratio, etc.)
2. Store in `typed_facts` table
3. Create index on field names + scheme ID

## Document Store Schema

```sql
-- Chunks table
CREATE TABLE chunks (
  chunk_id TEXT PRIMARY KEY,
  source_id TEXT,
  source_url TEXT,
  doc_version TEXT,
  fetched_at TIMESTAMP,
  chunk_type TEXT,
  section_path TEXT,
  text TEXT,
  fields_present JSON,
  vector_id TEXT,  -- Link to vector store
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- Typed facts table
CREATE TABLE typed_facts (
  fact_id TEXT PRIMARY KEY,
  scheme_id TEXT,
  field_name TEXT,
  field_value TEXT,
  data_type TEXT,
  as_of_date DATE,
  source_chunk_id TEXT,
  confidence FLOAT,
  FOREIGN KEY (source_chunk_id) REFERENCES chunks(chunk_id)
);

-- Evidence spans (link facts to source quotes)
CREATE TABLE evidence_spans (
  span_id TEXT PRIMARY KEY,
  fact_id TEXT,
  source_url TEXT,
  quote TEXT,
  page_number INT,
  FOREIGN KEY (fact_id) REFERENCES typed_facts(fact_id)
);
```

## Vector Store Structure

FAISS index files:
```
data/vector_store/
├── index.faiss          # Vector index (binary)
├── metadata.json        # Chunk → embedding mapping
└── config.json          # Dimension, distance metric, etc.
```

Metadata mapping:
```json
{
  "vectors": [
    {
      "vector_id": 0,
      "chunk_id": "link-03_chunk_001",
      "source_id": "link-03",
      "fields_present": ["min_sip", "expense_ratio"]
    },
    ...
  ]
}
```

## Retrieval Patterns

### Pattern 1: Numeric Field Query
```
User: "What is the expense ratio?"
1. Query typed_facts WHERE field_name='expense_ratio' AND scheme_id='navi_flexi_cap'
2. Return: { value: 0.35, as_of: 2026-03-05, source_url: ... }
3. No embedding needed (structured lookup)
```

### Pattern 2: Definition Query
```
User: "What is NAV?"
1. Semantic search in vector store: "NAV definition"
2. Retrieve top chunks with fields ['what_is_nav']
3. Prefer AMFI/SEBI sources (links 12+)
4. Return with citations
```

### Pattern 3: Scheme Info Query
```
User: "Tell me about Navi Flexi Cap"
1. Lookup typed_facts for all fields WHERE scheme_id='navi_flexi_cap'
2. Combine with semantic search for holdings, performance data
3. Return structured response
```

## Running Full Indexing

```bash
python phase3/index.py --mode full
```

This runs:
1. Setup doc store ✓
2. Embed all chunks ✓
3. Index all typed facts ✓
4. Validate indexes ✓
5. Write manifest ✓

## Output Verification

After indexing completes:

```bash
# Check chunk count
sqlite3 data/doc_store.db "SELECT COUNT(*) FROM chunks;"
# Expected: ~500-1000 chunks

# Check typed facts
sqlite3 data/doc_store.db "SELECT COUNT(*) FROM typed_facts;"
# Expected: ~100-300 facts

# Verify vector index
ls -lh data/vector_store/
# index.faiss should be ~10-50 MB
```

## Performance Tuning

- Vector dimension: 1536 (OpenAI default)
- Chunk batch size: 100
- Vector search: top-k=10
- Typed facts index: B-tree on scheme_id + field_name

## Testing Retrieval

```python
from phase3.lib.retriever import DualStoreRetriever

retriever = DualStoreRetriever()

# Numeric query
result = retriever.query_typed_fact("navi_flexi_cap", "expense_ratio")
print(result)  # { value: 0.35, as_of: ..., evidence: ... }

# Semantic query
results = retriever.semantic_search("what is exit load?", top_k=5)
print(results)  # [ {chunk_id, text, score}, ... ]
```

## Next Step

Proceed to **Phase 4** to build the API and safety guardrails using these indexes.
