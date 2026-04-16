from fastapi import APIRouter, Request

from memory_service.models import DeleteRequest, DeleteResponse

router = APIRouter()


@router.delete("/entries", response_model=DeleteResponse)
async def delete_entries(body: DeleteRequest, request: Request):
    db = request.app.state.db
    deleted = await db.delete(body.entry_ids)
    return DeleteResponse(deleted=deleted)
