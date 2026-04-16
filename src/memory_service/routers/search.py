from fastapi import APIRouter, Request

from memory_service.models import SearchRequest, SearchResponse, SearchResult

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest, request: Request):
    embedder = request.app.state.embedder
    db = request.app.state.db

    query_vector = embedder.encode_query(body.query)

    rows = await db.search(
        query_vector,
        workspace_id=body.workspace_id,
        memory_type=body.memory_type,
        date_from=body.date_from,
        date_to=body.date_to,
        limit=body.limit,
    )

    results = [SearchResult(entry_id=r["entry_id"], score=r["score"]) for r in rows]
    return SearchResponse(results=results)
