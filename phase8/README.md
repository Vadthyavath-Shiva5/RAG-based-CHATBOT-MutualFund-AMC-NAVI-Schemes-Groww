# Phase 8: Deployment Architecture and Rollout Plan

Phase 8 converts the project from local development (`phase4` + `phase6` running manually)
into a secure, always-on cloud deployment.

## Goals
- Push code to GitHub with zero leaked secrets.
- Deploy backend, frontend, and scheduler as managed services.
- Preserve index/data persistence across restarts.
- Enforce security and quality gates before public release.

## Recommended Deployment Path

Primary path:
1. GitHub hardening and repository cleanup
2. Render staging deployment
3. Phase 7 evaluation gate in staging
4. Production deployment

Alternative paths:
- Hugging Face Spaces for demo-only hosting
- VPS for full control/self-managed infrastructure

## Target Runtime Architecture

```text
Users
  |
  v
Frontend Service (phase6/app.py)
  |
  v
Backend API Service (phase4/app.py)
  |
  +--> LLM Provider API
  |
  +--> Persistent data volume (doc store, chunks, vector metadata)
  |
  +--> Scheduler Worker (phase5/scheduler.py --mode start)
        updates raw/parsed/chunks/indexes on schedule
```

## Pre-GitHub Security Checklist (Mandatory)

1. Rotate all exposed API keys immediately.
2. Remove secrets from source files and commit history.
3. Ensure `.env` is ignored and never committed.
4. Keep only `.env.example` with placeholder values.
5. Run secret scanning before every push.
6. Disable debug mode for hosted environments.
7. Restrict CORS to known frontend domains in production.
8. Add rate limiting for `/chat`.

## Repository Changes Needed Before Deployment

1. Add/update `.gitignore` for `.env`, caches, logs, and build artifacts.
2. Add `.env.example` with deployment variables.
3. Add cloud config files (`render.yaml`, Docker files, or compose files).
4. Document startup commands and health checks.
5. Ensure `phase7` runner is part of deployment gate.

Current repository status:
- `.gitignore` hardened
- `.env.example` added
- `render.yaml` added (Render blueprint template)

## Render Deployment Blueprint (Recommended)

Create three services using **Render Blueprint** from `render.yaml`:

1. Backend Web Service
- Start command: `python phase4/app.py`
- Health check: `/health`
- Persistent disk mounted for `data/`

2. Frontend Web Service
- Start command: `python phase6/app.py`
- Env var `BACKEND_API_BASE_URL` pointing to backend public URL

3. Scheduler Worker or Cron
- Command: `python -m phase5.scheduler --mode start --interval-minutes 60`
- Uses same persistent `data/` storage strategy

If Render asks for a single start command:
- That flow is for creating one standalone service.
- Cancel that flow and create a **Blueprint** deploy so all three services are created together.

## Hugging Face Spaces Blueprint (Demo Path)

1. Use Docker Space for compatibility with Flask stack.
2. Set secrets in Space settings, never in repository.
3. Prefer single-service demo architecture.
4. Treat as demo/preview because continuous scheduler + persistence is limited compared to Render/VPS.

## VPS Blueprint (Self-Managed Path)

1. Use Docker Compose with separate backend, frontend, scheduler containers.
2. Put Nginx/Caddy in front for HTTPS termination and routing.
3. Use systemd to auto-start stack on reboot.
4. Lock firewall to required ports only.
5. Schedule backups for `data/` and manifests.

## Required Environment Variables (Production)

Core:
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_API_KEY` (if embedding provider requires it)

Backend:
- `API_HOST`
- `API_PORT`
- `API_DEBUG=false`
- `DATA_DIR`

Frontend:
- `FRONTEND_HOST`
- `FRONTEND_PORT`
- `BACKEND_API_BASE_URL`

Scheduler:
- `SCHEDULER_ENABLED`
- `SCHEDULER_TIMEZONE`
- `REFRESH_SCHEDULE_CRON`

## Quality Gates Before Go-Live

1. Phase 7 full run passes thresholds or approved exception list exists.
2. Health endpoint and chat endpoint are stable under smoke load.
3. `/sources` freshness updates correctly after scheduler run.
4. Security checklist is fully complete.
5. Backups and rollback are tested at least once.

## Observability and Operations

Track these at minimum:
- API latency and error rate
- refusal and PII safety flags
- grounding/citation presence
- scheduler run success/failure
- data freshness staleness (`/sources`)

## Rollback Strategy

1. Keep previous deploy artifact/image tag.
2. Roll back by redeploying previous known-good version.
3. Restore data snapshot if corruption is detected.
4. Re-run Phase 7 smoke suite after rollback.

## Definition of Done for Phase 8

Phase 8 is complete when:
1. Public URL serves frontend reliably.
2. Frontend and backend communicate securely over cloud URLs.
3. Scheduler runs automatically and freshness updates are visible.
4. Secrets are fully managed outside code.
5. Phase 7 gate is integrated in release workflow.
