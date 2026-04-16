import logging
from datetime import date

from fastapi import APIRouter, Request

from memory_service.models import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(body: IngestRequest, request: Request):
    embedder = request.app.state.embedder
    db = request.app.state.db

    texts = [entry.content for entry in body.entries]
    vectors = embedder.encode_documents(texts)

    records = []
    for entry, vector in zip(body.entries, vectors):
        records.append({
            "entry_id": entry.id,
            "embedding": vector,
            "workspace_id": entry.workspace_id,
            "memory_type": entry.memory_type,
            "date": date.fromisoformat(entry.date),
        })

    await db.upsert(records)
    logger.info("Ingested %d entries", len(records))
    return IngestResponse(ingested=len(records))
