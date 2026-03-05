# Getting Started

## 1. Install
```bash
pip install -r requirements.txt
```

## 2. Configure
Create `.env` in project root and set at least:
- `LLM_API_KEY`
- `EMBEDDING_API_KEY`

## 3. Ingest data (optional if already done)
```bash
python phase1/run.py
```

## 4. Build indexes
```bash
python phase3/index.py --mode populate_doc_store
python phase3/index.py --mode embed_chunks
```

## 5. Start backend (Phase 4)
```bash
python phase4/app.py
```
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`

## 6. Start frontend (Phase 6)
```bash
python phase6/app.py
```
- UI: `http://localhost:3000`

If backend is on a different host/port:
```bash
set BACKEND_API_BASE_URL=http://localhost:8000
python phase6/app.py
```

## 7. Quick API test
```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"What is NAV?"}'
```

## 8. Scheduler (optional)
```bash
python phase5/scheduler.py --mode status
python phase5/scheduler.py --mode refresh
```
