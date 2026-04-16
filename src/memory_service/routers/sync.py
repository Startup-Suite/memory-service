from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

from memory_service.models import SyncResponse

router = APIRouter()


@router.get("/sync", response_model=SyncResponse)
async def sync(
    request: Request,
    since: str = Query(..., description="ISO 8601 timestamp"),
):
    db = request.app.state.db
    since_dt = datetime.fromisoformat(since).astimezone(timezone.utc)
    entry_ids = await db.list_since(since_dt)
    return SyncResponse(entry_ids=entry_ids)
