from pydantic import BaseModel


class MemoryEntry(BaseModel):
    id: str
    content: str
    memory_type: str = "daily"
    date: str
    workspace_id: str | None = None
    metadata: dict = {}


class IngestRequest(BaseModel):
    entries: list[MemoryEntry]


class IngestResponse(BaseModel):
    ingested: int


class SearchRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    memory_type: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 10


class SearchResult(BaseModel):
    entry_id: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class DeleteRequest(BaseModel):
    entry_ids: list[str]


class DeleteResponse(BaseModel):
    deleted: int


class SyncResponse(BaseModel):
    entry_ids: list[str]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
