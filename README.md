# Startup Suite Memory Service

Semantic search over organizational memory entries. Receives entries from the [Startup Suite core](https://github.com/Startup-Suite/core) app, embeds them with `BAAI/bge-large-en-v1.5`, and serves vector similarity search via a REST API.

Part of [ADR 0033 — Org-Level Context Management](https://github.com/Startup-Suite/core/blob/main/docs/decisions/0033-org-level-context-management.md), Phase 3.

## Architecture

Two containers on dedicated GPU hardware:

- **memory-service** — Python FastAPI app. Loads the embedding model on startup, embeds incoming entries, stores vectors in Postgres, serves search queries.
- **postgres** — `pgvector/pgvector:pg17`. Stores embeddings with cosine distance search. Schema is auto-created on startup.

The core Elixir app talks to this service via its `Platform.Memory.Providers.StartupSuite` HTTP client. Entry IDs are UUIDv7s from the core app's `org_memory_entries` table — this service only stores the embedding and metadata, not the full content. Search results return `{entry_id, score}` and the core app hydrates from its own DB.

## REST API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ingest` | POST | Embed and store entries |
| `/search` | POST | Vector similarity search |
| `/entries` | DELETE | Remove entries from index |
| `/sync` | GET | List entry IDs ingested since a timestamp |
| `/health` | GET | Readiness check |

### POST /ingest

```json
// Request
{
  "entries": [{
    "id": "019abc00-0000-7000-8000-000000000001",
    "content": "We decided to use pgvector for the memory service.",
    "memory_type": "daily",
    "date": "2026-04-15",
    "workspace_id": null,
    "metadata": {}
  }]
}

// Response
{"ingested": 1}
```

### POST /search

```json
// Request
{
  "query": "what did we decide about the database",
  "workspace_id": null,
  "memory_type": "daily",
  "date_from": "2026-04-01",
  "date_to": "2026-04-15",
  "limit": 10
}

// Response
{"results": [{"entry_id": "019abc00-...", "score": 0.87}]}
```

### DELETE /entries

```json
// Request
{"entry_ids": ["019abc00-0000-7000-8000-000000000001"]}

// Response
{"deleted": 1}
```

### GET /sync?since=2026-04-01T00:00:00Z

```json
{"entry_ids": ["019abc00-0000-7000-8000-000000000001"]}
```

### GET /health

```json
{"status": "ok", "model_loaded": true}
```

Returns 503 with `"status": "loading"` while the embedding model is loading.

## Setup

### Prerequisites

- Docker with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- NVIDIA GPU with CUDA support

### Run

```bash
cp .env.example .env  # edit as needed
docker compose up -d --build
```

The embedding model (~1.3GB) downloads on first startup. Subsequent starts load from the Hugging Face cache.

### Local development (without Docker)

```bash
uv sync --all-extras
# Start a Postgres instance with pgvector (or use docker compose up postgres)
export MEMORY_DATABASE_URL=postgresql://memory:memory@localhost:5433/memory
export MEMORY_EMBEDDING_DEVICE=cpu  # or cuda
uv run uvicorn memory_service.main:app --reload --port 8100
```

### Tests

```bash
uv run pytest tests/ -v
```

Tests use a mock embedder and async mock DB — no GPU or Postgres required.

## Configuration

All settings use the `MEMORY_` env prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Hugging Face model ID |
| `MEMORY_EMBEDDING_DEVICE` | `cuda` | `cuda` or `cpu` |
| `MEMORY_DATABASE_URL` | `postgresql://memory:memory@localhost:5432/memory` | Postgres connection string |
| `MEMORY_API_KEY` | none | Optional shared secret (`X-API-Key` header) |
| `MEMORY_HOST` | `0.0.0.0` | Bind address |
| `MEMORY_PORT` | `8100` | Bind port |

## Tech Stack

- Python 3.12, FastAPI, uvicorn
- sentence-transformers (`BAAI/bge-large-en-v1.5`, 1024-dim)
- asyncpg + pgvector (Postgres 17)
- pydantic-settings for configuration
- uv for dependency management
