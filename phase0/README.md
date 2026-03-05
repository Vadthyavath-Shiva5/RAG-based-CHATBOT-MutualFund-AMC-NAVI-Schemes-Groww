# Phase 0: Configuration & Secrets Management

This phase sets up the foundational configuration infrastructure for the RAG chatbot.

## What This Phase Contains

- **sources.yaml**: Complete list of all 19 data sources with URLs, types (HTML/PDF), refresh frequencies, and allowed fields
- **.env.example**: Template for environment variables (API keys, model configs, paths)
- **config.py**: Python configuration loader that reads from .env and sources.yaml

## Key Files

- `sources.yaml` - Data source definitions
- `.env.example` - Environment template (copy to `.env` locally, never commit)
- `config.py` - Configuration management and validation

## Before Running Any Phase

1. Copy `.env.example` to `.env`:
   ```bash
   cp phase0/.env.example .env
   ```

2. Update `.env` with your actual API keys:
   ```
   LLM_API_KEY=sk-your-openai-key
   EMBEDDING_API_KEY=sk-your-openai-key
   ```

3. Verify sources.yaml contains all required URLs

## Security Note

**Never commit `.env` file to version control.** It contains sensitive API keys.

## Configuration Hierarchy

1. `.env` file (highest priority - local overrides)
2. `.env.example` (fallback defaults)
3. Code defaults (lowest priority)

## Next Step

Once configured, proceed to **Phase 1** for data ingestion and scraping.
