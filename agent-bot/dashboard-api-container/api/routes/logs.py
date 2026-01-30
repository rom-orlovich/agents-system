"""Log streaming endpoints."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/stream")
async def stream_logs():
    """Stream logs using SSE."""
    async def log_generator():
        while True:
            yield {"data": '{"level": "info", "message": "Sample log"}'}

    return EventSourceResponse(log_generator())


@router.get("/tasks/{task_id}")
async def get_task_logs(task_id: str) -> dict[str, list[str]]:
    """Get logs for specific task."""
    return {"logs": []}
