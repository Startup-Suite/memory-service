# Startup Suite Memory Service

Semantic search over organizational memory entries. Receives entries from the [Startup Suite core](https://github.com/Startup-Suite/core) app, embeds them with `BAAI/bge-large-en-v1.5`, and serves vector similarity search via a REST API.

Part of [ADR 0033 — Org-Level Context Management](https://github.com/Startup-Suite/core/blob/main/docs/decisions/0033-org-level-context-management.md), Phase 3.

## Architecture

memory-service is a FastAPI app that embeds content and stores vectors in a pgvector-enabled Postgres. It's a **search index only** — it does not store the entry content, just the embedding plus filter metadata (`workspace_id`, `memory_type`, `date`). Search returns `{entry_id, score}`; the caller rehydrates content from its own source of truth.

The core Elixir app talks to this service via its `Platform.Memory.Providers.StartupSuite` HTTP client. Entry IDs are UUIDv7s from the core app's `org_memory_entries` table.

### Embedding backend

Two interchangeable backends, selected by `MEMORY_EMBEDDING_BACKEND`:

- `local` (default) — loads the embedding model in-process via `sentence-transformers`. Needs a GPU (or CPU fallback). Simplest to deploy; zero-config for a single-host setup.
- `http` — calls out to an OpenAI-compatible `/v1/embeddings` endpoint (e.g. [Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference), vLLM with `--task embed`, etc.). Memory-service itself becomes GPU-free and deploys anywhere. Fits multi-service clusters where one embedding server is shared across consumers.

### Postgres

Any Postgres 14+ with the [`pgvector`](https://github.com/pgvector/pgvector) extension installed. Two common patterns:

- **Use the bundled container** — `docker compose up` starts `pgvector/pgvector:pg17` alongside the service. Zero config, good for single-host or evaluation.
- **Point at an existing pgvector-ready Postgres** — set `MEMORY_DATABASE_URL` at a database you already run (your core suite's Postgres, a managed service, etc.). You can share a server but use a separate database (`CREATE DATABASE memory; \c memory; CREATE EXTENSION vector;`) for clean blast-radius separation. No need to run a second Postgres.

Schema (one `embeddings` table + indexes) is auto-created on startup.

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

- Docker
- For `local` embedding backend: NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (or CPU — slow but works)
- For `http` embedding backend: a reachable OpenAI-compatible embedding server

### Run (bundled Postgres + local embedder)

```bash
cp .env.example .env  # edit as needed
docker compose up -d --build
```

The embedding model (~1.3GB) downloads on first startup. Subsequent starts load from the Hugging Face cache.

### Run with an existing Postgres and a remote embedder

```bash
# .env
MEMORY_EMBEDDING_BACKEND=http
MEMORY_EMBEDDING_URL=http://your-tei-host:8088
MEMORY_DATABASE_URL=postgresql://user:pass@your-pg-host:5432/memory
```

In this mode the bundled `postgres` service is unused — you can remove it from `docker-compose.yml` or just not start it. The service itself has no GPU requirement.

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
| `MEMORY_EMBEDDING_BACKEND` | `local` | `local` (in-process sentence-transformers) or `http` (remote OpenAI-compatible server) |
| `MEMORY_EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Hugging Face model ID (used by both backends — must match the model the remote server serves when `BACKEND=http`) |
| `MEMORY_EMBEDDING_DEVICE` | `cuda` | `cuda` or `cpu`. Only used when `BACKEND=local` |
| `MEMORY_EMBEDDING_URL` | none | Required when `BACKEND=http`. e.g. `http://tei-host:8088` |
| `MEMORY_DATABASE_URL` | `postgresql://memory:memory@localhost:5432/memory` | Postgres connection string. Must be pgvector-capable. |
| `MEMORY_API_KEY` | none | Optional shared secret (`X-API-Key` header) |
| `MEMORY_HOST` | `0.0.0.0` | Bind address |
| `MEMORY_PORT` | `8100` | Bind port |

## Tech Stack

- Python 3.12, FastAPI, uvicorn
- sentence-transformers or httpx (depending on embedding backend)
- Default model: `BAAI/bge-large-en-v1.5` (1024-dim)
- asyncpg + pgvector (any Postgres 14+ with the `vector` extension)
- pydantic-settings for configuration
- uv for dependency management
