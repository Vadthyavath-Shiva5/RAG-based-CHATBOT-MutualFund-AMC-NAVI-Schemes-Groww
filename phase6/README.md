# Phase 6: Frontend UI/UX

Phase 6 is the dedicated frontend layer for the chatbot.

## Scope
- Landing page + chat widget UI
- Quick question chips and FAQ interactions
- Calls backend API over HTTP (`/chat`) with CORS
- Source links rendered in chat responses

## Files
- `phase6/app.py` - Flask static frontend server
- `phase6/static/index.html` - UI shell
- `phase6/static/js/main.js` - page interactions
- `phase6/static/js/chat.js` - chat client + API calls
- `phase6/static/css/style.css` - styles

## Run Frontend
```bash
python phase6/app.py
```

Default URL: `http://localhost:3000`

## Backend URL Configuration
Frontend reads backend API base URL from `BACKEND_API_BASE_URL`.

Example:
```bash
set BACKEND_API_BASE_URL=http://localhost:8000
python phase6/app.py
```

If unset, default backend is `http://localhost:8000`.

## Full Local Run
1. Start backend: `python phase4/app.py`
2. Start frontend: `python phase6/app.py`
3. Open `http://localhost:3000`
