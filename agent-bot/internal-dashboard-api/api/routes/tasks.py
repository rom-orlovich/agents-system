from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from services import TaskManager

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
task_manager = TaskManager()


@router.get("")
async def list_tasks(
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    tasks = await task_manager.list_tasks(status, limit, offset)
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/stats")
async def get_task_stats():
    return await task_manager.get_task_stats()


@router.get("/queue")
async def get_queue_info():
    length = await task_manager.get_queue_length()
    return {"queue_length": length}


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = await task_manager.get_task(task_id)
    if task:
        return task
    return JSONResponse(status_code=404, content={"error": "Task not found"})


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    success = await task_manager.cancel_task(task_id)
    if success:
        return {"status": "cancelled", "task_id": task_id}
    return JSONResponse(status_code=404, content={"error": "Task not found"})
