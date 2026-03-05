# Phase 1: Data Ingestion & Normalization

This phase scrapes all data sources and normalizes them into typed, structured formats.

## What This Phase Does

**1A) Source Acquisition**
- Scrapes HTML pages (Groww scheme pages) using Playwright
- Extracts PDFs (Navi official documents) using pdfplumber/pypdf
- Implements rate limiting, retries, user-agent rotation
- Stores raw HTML/PDF snapshots

**1B) Normalization**
- Extracts clean text from raw content
- Converts to typed JSON fields (scheme name, NAV, expense ratio, exit load, etc.)
- Enriches numeric fields with metadata (as_of_date, source_run_id)
- Creates evidence spans linking facts to source quotes

**1C) Storage**
```
data/
├── raw/           # Original HTML/PDF files per source
├── parsed/        # Cleaned text + extracted structured data
├── chunks/        # JSONL chunks (prepared for Phase 2)
└── manifests/     # Run metadata: timestamp, hashes, diffs
```

## Key Files

- `run.py` - Main orchestrator (runs the full ingestion pipeline)
- `lib/fetching.py` - Web scraping (Playwright, requests, with rate limiting)
- `lib/pdf_parse.py` - PDF text extraction with section detection
- `lib/html_parse.py` - HTML cleaning and table extraction
- `lib/normalize.py` - Typed field extraction and validation
- `lib/chunking.py` - Chunk preparation for retrieval
- `lib/util.py` - Helpers (logging, hashing, file ops)

## Typed Fields Example

```json
{
  "source_id": "link-03",
  "source_run_id": "2026-03-05T10:30:00Z",
  "scheme": {
    "name": "Navi Flexi Cap",
    "nav": {
      "value": 45.32,
      "as_of": "2026-03-05",
      "currency": "INR"
    },
    "min_sip": {
      "value": 100,
      "currency": "INR"
    },
    "expense_ratio": {
      "value": 0.35,
      "unit": "percent_per_annum"
    },
    "exit_load": "0% if held > 1 year",
    "lock_in": null,
    "risk_label": "High",
    "aum": {
      "value": 1250000000,
      "as_of": "2026-03-05",
      "currency": "INR"
    }
  },
  "evidence": {
    "url": "https://groww.in/mutual-funds/navi-flexi-cap-direct-growth",
    "fetched_at": "2026-03-05T10:30:00Z",
    "quote": "Expense Ratio: 0.35% p.a."
  }
}
```

## Running Phase 1

```bash
python phase1/run.py
```

This will:
1. Read sources from `phase0/sources.yaml`
2. Fetch all sources (respecting rate limits)
3. Parse and normalize data
4. Store results in `data/` folders
5. Generate `data/manifests/run_TIMESTAMP.json`

## Output Structure

After Phase 1 completes:
```
data/
├── raw/
│   ├── link-01_groww_amc/
│   │   ├── snapshot.html
│   │   └── meta.json
│   ├── link-03_navi_flexi_cap/
│   │   ├── snapshot.html
│   │   └── tables.json
│   └── ...
├── parsed/
│   ├── link-01_groww_amc/
│   │   ├── text.txt
│   │   └── structured.json
│   └── ...
├── chunks/
│   ├── link-01_groww_amc.jsonl
│   ├── link-03_navi_flexi_cap.jsonl
│   └── ...
└── manifests/
    └── run_2026-03-05T103000Z.json
```

## Next Step

Proceed to **Phase 2** for document processing and hybrid chunking.
