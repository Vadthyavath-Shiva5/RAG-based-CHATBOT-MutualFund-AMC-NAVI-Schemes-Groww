# Phase 7: Evaluation and Testing

Phase 7 is implemented as an executable evaluation layer for the chatbot backend.

## Scope
- In-scope factual validation (grounding + numeric checks)
- Refusal accuracy validation (true/false positives)
- PII blocking validation
- Freshness/staleness extraction from `/sources`
- JSON report generation for auditability

## Files Implemented
- `phase7/test_datasets.py`
  - Curated test cases for:
    - `IN_SCOPE_CASES`
    - `REFUSAL_CASES`
    - `PII_CASES`
    - `TEST_THRESHOLDS`
- `phase7/lib/metrics.py`
  - Metric computation:
    - `grounding_rate`
    - `numeric_correctness`
    - `refusal_accuracy`
    - `pii_detection_rate`
    - staleness days from latest data timestamp
- `phase7/lib/test_runner.py`
  - CLI runner for all test modes
  - Calls Phase 4 API endpoints directly (`/health`, `/chat`, `/sources`)
  - Prints terminal summary and writes JSON report
- `phase7/test_integration.py`
  - `pytest` integration checks against a running backend

## Run Commands

Start backend first:
```bash
python phase4/app.py
```

Then run Phase 7:
```bash
# Full suite (also writes report to phase7/reports/)
python phase7/lib/test_runner.py --mode full

# Only in-scope checks
python phase7/lib/test_runner.py --mode in_scope

# Only refusal checks
python phase7/lib/test_runner.py --mode refusal

# Only PII checks
python phase7/lib/test_runner.py --mode pii

# Explicit report path
python phase7/lib/test_runner.py --mode report --output phase7/reports/latest_report.json

# Fail process when thresholds are missed
python phase7/lib/test_runner.py --mode full --fail-on-threshold
```

Optional backend override:
```bash
python phase7/lib/test_runner.py --mode full --base-url http://127.0.0.1:8000
```

## Integration Tests
```bash
pytest phase7/test_integration.py -v
```

If backend is not reachable, tests are skipped with a clear message.

## Output

Generated JSON report includes:
- run metadata (`run_at`, `mode`, `backend_base_url`)
- health check and data freshness summary
- per-case results for in-scope/refusal/PII
- metric cards with target thresholds and pass/fail
- overall status (`PASS` / `FAIL`)

Default report directory:
```text
phase7/reports/
```

## Next
Proceed to Phase 8 deployment planning once Phase 7 metrics pass your quality thresholds.

