# CLAUDE.md

## Project Overview

Startup Suite Memory Service — a standalone FastAPI microservice providing semantic vector search over organizational memory entries. Receives entries from the Startup Suite core Elixir app, embeds them using `BAAI/bge-large-en-v1.5` (1024-dim), stores embeddings in Postgres via pgvector, and serves similarity search.

Designed per [ADR 0033](https://github.com/Startup-Suite/core/blob/main/docs/decisions/0033-org-level-context-management.md), Phase 3.4.

## Commands

```bash
uv sync --all-extras          # Install all deps including dev
uv run pytest tests/ -v       # Run tests (no GPU/Postgres needed)
uv run uvicorn memory_service.main:app --reload --port 8100  # Dev server

docker compose up -d --build  # Production: build and start both containers
docker compose up postgres    # Just Postgres for local dev
docker compose logs -f memory-service  # Tail logs
```

## Architecture

```
src/memory_service/
  main.py        — FastAPI app, lifespan (model load + DB init), health endpoint
  config.py      — pydantic-settings, MEMORY_ env prefix
  models.py      — Pydantic request/response schemas
  embedder.py    — SentenceTransformer wrapper, query prefix, CUDA support
  db.py          — asyncpg + pgvector: upsert, cosine search, delete, sync
  routers/
    ingest.py    — POST /ingest (embed + store)
    search.py    — POST /search (vector similarity)
    entries.py   — DELETE /entries (remove from index)
    sync.py      — GET /sync (catchup by timestamp)
```

### Key patterns

- **Lifespan**: Embedder and DB pool are created during FastAPI lifespan startup, stored on `app.state`, cleaned up on shutdown.
- **DB schema auto-migration**: `VectorDB.create()` runs `CREATE TABLE IF NOT EXISTS` on startup. No migration tool.
- **Idempotent upsert**: `INSERT ON CONFLICT (entry_id) DO UPDATE` — re-ingesting the same entry overwrites the embedding.
- **Cosine similarity**: `1 - (embedding <=> $1)` gives a 0-1 score. Results ordered by distance ascending.
- **BGE query prefix**: `encode_query()` prepends `"Represent this sentence for searching relevant passages: "` per model documentation. `encode_documents()` does not prefix.

### Integration with core app

- Core app's `Platform.Memory.Providers.StartupSuite` (Elixir, Req HTTP client) calls this service.
- Entry IDs are UUIDv7s from core's `org_memory_entries` table.
- This service stores only embeddings + metadata, not full content.
- Search returns `{entry_id, score}` — core hydrates full entries from its own DB.
- Telemetry event `[:platform, :org, :memory_entry_written]` triggers ingest calls (~5-50/day).

## Database

Single `embeddings` table in dedicated Postgres with pgvector extension:

| Column | Type | Notes |
|--------|------|-------|
| entry_id | UUID PK | From core app's org_memory_entries |
| embedding | vector(1024) | Normalized, cosine distance |
| workspace_id | UUID nullable | For multi-tenancy filtering |
| memory_type | TEXT | "daily" or "long_term" |
| date | DATE | Relevant date for the entry |
| ingested_at | TIMESTAMPTZ | For /sync catchup endpoint |

At current scale (<20K rows/year), no vector index is needed — exact scan is sub-millisecond.

## Testing

- Tests use `FakeEmbedder` (deterministic vectors from content hash) and `AsyncMock` DB.
- No GPU or Postgres required to run tests.
- `conftest.py` provides `client`, `fake_embedder`, and `mock_db` fixtures.

## Rules

- Use `asyncpg` for all Postgres access (not psycopg2, sqlalchemy).
- Use `Req`-compatible JSON shapes — the core app's HTTP client expects the exact request/response schemas in `models.py`.
- Never store full entry content in this service — only embeddings and metadata.
- All env vars use the `MEMORY_` prefix.
