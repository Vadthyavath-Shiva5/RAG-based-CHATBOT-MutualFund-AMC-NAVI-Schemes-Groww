# RAG-based Chatbot for Navi AMC Mutual Fund Schemes

This project is a multi-phase RAG chatbot system focused on:
- Navi AMC scheme facts
- Mutual fund education
- Safety-first responses with refusal and PII guardrails

Data sources include Groww, AMFI, and SEBI content.

## Architecture by Phase

- `phase0`: configuration and source policy
- `phase1`: ingestion (raw fetch + parsing)
- `phase2`: chunk processing
- `phase3`: indexing (FAISS + document store)
- `phase4`: backend API and guardrails (Flask)
- `phase5`: scheduler and refresh propagation
- `phase6`: frontend UI/UX (Flask static app)
- `phase7`: evaluation suite (datasets, metrics, runner, integration tests)
- `phase8`: deployment architecture and rollout plan

Detailed phase architecture is documented in each phase folder.

## Local Run

1. Install dependencies
```bash
pip install -r requirements.txt
```

2. Build indexes if required
```bash
python phase1/run.py
python phase3/index.py --mode populate_doc_store
python phase3/index.py --mode embed_chunks
```

3. Start backend (terminal 1)
```bash
python phase4/app.py
```
Backend URL: `http://localhost:8000`

4. Start frontend (terminal 2)
```bash
python phase6/app.py
```
Frontend URL: `http://localhost:3000`

Optional frontend backend override:
```bash
set BACKEND_API_BASE_URL=http://localhost:8000
python phase6/app.py
```

## Core Backend Endpoints

- `GET /`
- `GET /health`
- `POST /chat`
- `GET /schemes`
- `GET /faq`
- `GET /sources`

## Testing and Evaluation (Phase 7)

Run evaluation runner:
```bash
python phase7/lib/test_runner.py --mode full
```

Run integration tests:
```bash
pytest phase7/test_integration.py -v
```

## Deployment Plan (Phase 8)

Deployment architecture and execution details are in:
- `phase8/README.md`

Current recommended path:
1. Security hardening and secret cleanup before GitHub push
2. Render-first cloud deployment (frontend + backend + scheduler)
3. Phase 7 quality gate before production
4. Optional alternatives: Hugging Face (demo), VPS (full control)

Render note:
- `render.yaml` defines three services (backend, frontend, scheduler) and must be deployed via Render Blueprint.
- If Render asks for only one start command, you are creating a single Web Service manually instead of a Blueprint deploy.

## Security Notes

- Never commit `.env` or API keys.
- Rotate keys immediately if exposed.
- Restrict production CORS and disable debug mode.
- Keep refusal and PII guardrails enabled.

## Pre-Deployment Files Added

These files are now in place to support secure GitHub push and cloud deployment:
- `.gitignore` hardened for env files, caches, logs, and evaluation artifacts
- `.env.example` with placeholder-only deployment variables
- `render.yaml` template for backend + frontend + scheduler deployment

## Production Hardening Toggles

Configured in `phase0/config.py` and consumed by backend:
- `CORS_ALLOW_ORIGINS` (comma-separated allowlist; `*` for local dev)
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`
- `RATE_LIMIT_WINDOW_SECONDS`

Defaults are set to keep local development behavior unchanged.
