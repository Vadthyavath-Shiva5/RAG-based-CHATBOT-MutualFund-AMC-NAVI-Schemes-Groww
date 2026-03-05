# Phase 4: Backend API & Guardrails

Phase 4 now contains backend APIs only.

## Scope
- Flask API service for chat and metadata endpoints
- Safety checks (PII + out-of-scope/advice blocking)
- Retrieval + LLM response pipeline
- JSON responses consumed by the Phase 6 frontend

## Run
```bash
python phase4/app.py
```

Default URL: `http://localhost:8000`

## Endpoints
- `GET /` - API service info
- `GET /health` - component health
- `POST /chat` - chat response endpoint
- `GET /schemes` - available schemes
- `GET /faq` - FAQ list
- `GET /sources` - source metadata

## Notes
- Frontend is no longer served from `phase4`.
- Start UI separately from `phase6/app.py`.
