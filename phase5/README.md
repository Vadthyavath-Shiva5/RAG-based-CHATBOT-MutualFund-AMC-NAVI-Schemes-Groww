# Phase 5: Scheduler & Refresh Pipeline

This phase automates weekly data refresh with incremental updates cascading through the entire pipeline.

## What This Phase Does

**5A) Weekly Refresh**
- Groww scheme numerics (NAV, AUM, returns): weekly
- Groww Navi AMC page: weekly
- AMFI/SEBI education: monthly/quarterly
- PDFs: by version hash (reprocess when URL changes)

**5B) Scheduler Workflow**
1. Fetch source (check timestamp vs cache)
2. Parse & normalize (extract updated facts)
3. Diff against previous run (identify changes)
4. If changed: regenerate chunks → re-embed → update vector index
5. Write run manifest & audit log

**5C) Propagation**
Changed fact → canonical facts store → derived chunks → vector index → API response

## Key Files

- `scheduler.py` - APScheduler-based job coordinator
- `lib/differ.py` - Detect changes between runs
- `lib/incremental.py` - Update only affected chunks/embeddings

## Running the Scheduler

```bash
# Start scheduler in background
python phase5/scheduler.py --mode start

# Check job status
python phase5/scheduler.py --mode status

# Manually trigger refresh
python phase5/scheduler.py --mode refresh --links link-01,link-03,link-09
```

## Scheduler Configuration

In `.env`:
```
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=UTC
REFRESH_SCHEDULE_CRON=0 2 * * 0  # Every Sunday at 2 AM UTC
```

Or in `sources.yaml`:
```yaml
sources:
  - id: link-03
    refresh_frequency: weekly      # Fetched every 7 days
  - id: link-11
    refresh_frequency: quarterly   # Fetched every 90 days
```

## Incremental Update Flow

```
Source Change Detected
  ↓
Reprocess only changed source
  ↓
Diff typed facts against previous
  ↓
If fact value changed:
  - Update typed_facts table ✓
  - Mark affected chunks ✓
  - Re-embed marked chunks ✓
  - Update vector index ✓
  ↓
Update last_refreshed timestamp ✓
Send refresh notification ✓
```

## Run Manifest

After each refresh, creates manifest:
```json
{
  "run_id": "2026-03-05T020000Z",
  "timestamp": "2026-03-05T02:00:00Z",
  "trigger": "scheduled",
  "sources_refreshed": [
    {
      "source_id": "link-03",
      "url": "https://groww.in/mutual-funds/navi-flexi-cap-direct-growth",
      "status": "success",
      "changed": true,
      "facts_changed": [
        { "scheme_id": "navi_flexi_cap", "field": "nav", "old": 43.12, "new": 45.32 },
        { "scheme_id": "navi_flexi_cap", "field": "aum", "old": 1200000000, "new": 1250000000 }
      ],
      "chunks_regenerated": 5,
      "embeddings_updated": 5
    }
  ],
  "propagation": {
    "doc_store_updated": true,
    "vector_index_updated": true,
    "api_ready": true
  },
  "duration_seconds": 42
}
```

## Monitoring Freshness

API endpoint `/sources` shows:
```json
{
  "sources": [
    {
      "source_id": "link-03",
      "last_refreshed": "2026-03-05T02:00:00Z",
      "days_since_refresh": 0,
      "next_refresh": "2026-03-12T02:00:00Z",
      "status": "fresh"
    }
  ]
}
```

## Handling Failures

If refresh fails for a source:
1. Keep previous version (safe fallback)
2. Log error with retry strategy
3. Try again in 1 hour (exponential backoff)
4. Alert after 3 failed attempts
5. Expose status in API `/sources` endpoint

## Testing Incremental Updates

```bash
# Simulate a source change
python phase5/scheduler.py --mode test_diff --source link-03

# Expected output: Shows what chunks would be regenerated
```

## Next Step

Proceed to **Phase 6** for the frontend UI.
