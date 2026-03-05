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


Detailed phase Architecture is noted in individual phase folder.
