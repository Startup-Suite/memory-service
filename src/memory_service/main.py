import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Security
from fastapi.security import APIKeyHeader

from memory_service.config import get_settings
from memory_service.db import VectorDB
from memory_service.embedder import Embedder
from memory_service.models import HealthResponse
from memory_service.routers import entries, ingest, search, sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    embedder = Embedder(settings.embedding_model, settings.embedding_device)
    app.state.embedder = embedder

    db = await VectorDB.create(settings.database_url, embedder.dimension)
    app.state.db = db

    logger.info("Memory service ready")
    yield

    await db.close()
    logger.info("Memory service shut down")


app = FastAPI(title="Startup Suite Memory Service", lifespan=lifespan)
app.include_router(ingest.router)
app.include_router(search.router)
app.include_router(entries.router)
app.include_router(sync.router)


@app.get("/health", response_model=HealthResponse)
async def health():
    model_loaded = hasattr(app.state, "embedder")
    db_ok = hasattr(app.state, "db")
    if model_loaded and db_ok:
        return HealthResponse(status="ok", model_loaded=True)
    return HealthResponse(status="loading", model_loaded=model_loaded)
