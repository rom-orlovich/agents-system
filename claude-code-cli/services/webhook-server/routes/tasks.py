"""Task management and log streaming API endpoints."""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from task_queue import RedisQueue
from models import TaskStatus

router = APIRouter()
queue = RedisQueue()


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get task details.

    Args:
        task_id: Task identifier

    Returns:
        Task data and metadata
    """
    await queue.connect()

    task_data = await queue.get_task(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get additional metadata from Redis hash
    task_metadata = await queue.redis.hgetall(f"tasks:{task_id}")

    return {
        "task_id": task_id,
        "data": task_data,
        "metadata": task_metadata
    }


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    offset: int = Query(0, ge=0, description="Starting log index"),
    limit: int = Query(100, ge=-1, le=1000, description="Number of logs to return (-1 for all)"),
    follow: bool = Query(False, description="Keep connection open for streaming (not implemented yet)")
):
    """Get streaming logs for a task.

    Args:
        task_id: Task identifier
        offset: Starting log index (default 0)
        limit: Number of logs to return (default 100, -1 for all)
        follow: Keep connection open for streaming (future feature)

    Returns:
        List of log entries with timestamps
    """
    await queue.connect()

    # Check if task exists
    task_data = await queue.get_task(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get logs
    logs = await queue.get_task_logs(task_id, offset=offset, limit=limit)

    # Get total log count
    total_logs = await queue.redis.llen(f"tasks:{task_id}:logs")

    return {
        "task_id": task_id,
        "logs": logs,
        "offset": offset,
        "limit": limit,
        "total": total_logs,
        "has_more": (offset + len(logs)) < total_logs if limit != -1 else False
    }


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    """Get task status.

    Args:
        task_id: Task identifier

    Returns:
        Task status and metadata
    """
    await queue.connect()

    # Get status from Redis hash
    status = await queue.redis.hget(f"tasks:{task_id}", "status")
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get other metadata
    metadata = await queue.redis.hgetall(f"tasks:{task_id}")

    return {
        "task_id": task_id,
        "status": status,
        "metadata": metadata
    }


@router.get("/")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max tasks to return")
):
    """List all tasks with optional status filter.

    Args:
        status: Filter by status (optional)
        limit: Max tasks to return (default 50)

    Returns:
        List of tasks
    """
    await queue.connect()

    # Convert status string to enum if provided
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Get all tasks
    tasks = await queue.get_all_tasks(status=status_filter)

    # Limit results
    tasks = tasks[:limit]

    return {
        "tasks": tasks,
        "count": len(tasks),
        "limit": limit
    }
