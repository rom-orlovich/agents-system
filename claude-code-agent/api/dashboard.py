"""Dashboard API endpoints."""

from datetime import datetime
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.database.models import TaskDB, SessionDB
from core.database.redis_client import redis_client
from shared import (
    Task,
    TaskStatus,
    AgentType,
    APIResponse,
    ChatMessage,
)
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/status")
async def get_status(request: Request):
    """Get machine status."""
    queue_length = await redis_client.queue_length()
    return {
        "machine_id": "claude-agent-001",
        "status": "online",
        "queue_length": queue_length,
        "sessions": request.app.state.ws_hub.get_session_count(),
        "connections": request.app.state.ws_hub.get_connection_count(),
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get session details."""
    result = await session.execute(
        select(SessionDB).where(SessionDB.session_id == session_id)
    )
    session_db = result.scalar_one_or_none()

    if not session_db:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_db.session_id,
        "user_id": session_db.user_id,
        "machine_id": session_db.machine_id,
        "connected_at": session_db.connected_at.isoformat(),
        "total_cost_usd": session_db.total_cost_usd,
        "total_tasks": session_db.total_tasks,
    }


@router.get("/tasks")
async def list_tasks(
    session_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session)
):
    """List tasks with optional filters."""
    query = select(TaskDB).order_by(TaskDB.created_at.desc()).limit(limit)

    if session_id:
        query = query.where(TaskDB.session_id == session_id)
    if status:
        query = query.where(TaskDB.status == status)

    result = await session.execute(query)
    tasks = result.scalars().all()

    return [
        {
            "task_id": task.task_id,
            "session_id": task.session_id,
            "status": task.status,
            "assigned_agent": task.assigned_agent,
            "agent_type": task.agent_type,
            "created_at": task.created_at.isoformat(),
            "cost_usd": task.cost_usd,
            "input_message": task.input_message[:200],  # Truncate
        }
        for task in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get task details."""
    result = await session.execute(
        select(TaskDB).where(TaskDB.task_id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "session_id": task.session_id,
        "user_id": task.user_id,
        "status": task.status,
        "assigned_agent": task.assigned_agent,
        "agent_type": task.agent_type,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "input_message": task.input_message,
        "output_stream": task.output_stream,
        "result": task.result,
        "error": task.error,
        "cost_usd": task.cost_usd,
        "input_tokens": task.input_tokens,
        "output_tokens": task.output_tokens,
        "duration_seconds": task.duration_seconds,
        "source": task.source,
    }


@router.post("/tasks/{task_id}/stop")
async def stop_task(
    task_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Stop a running task."""
    result = await session.execute(
        select(TaskDB).where(TaskDB.task_id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
        return APIResponse(
            success=False,
            message=f"Cannot stop task in status: {task.status}"
        )

    # Update status
    task.status = TaskStatus.CANCELLED
    await session.commit()

    # Update Redis
    await redis_client.set_task_status(task_id, TaskStatus.CANCELLED)

    logger.info("Task stopped", task_id=task_id)

    return APIResponse(
        success=True,
        message="Task stopped successfully"
    )


@router.post("/chat")
async def chat_with_brain(
    message: ChatMessage,
    session_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Send chat message to Brain."""
    # Create or get session
    result = await session.execute(
        select(SessionDB).where(SessionDB.session_id == session_id)
    )
    session_db = result.scalar_one_or_none()

    if not session_db:
        # Create new session
        session_db = SessionDB(
            session_id=session_id,
            user_id="default-user",  # TODO: Get from auth
            machine_id="claude-agent-001",
            connected_at=datetime.utcnow(),
        )
        session.add(session_db)
        await session.commit()

    # Create task
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    task_db = TaskDB(
        task_id=task_id,
        session_id=session_id,
        user_id=session_db.user_id,
        assigned_agent="brain",
        agent_type=AgentType.PLANNING,
        status=TaskStatus.QUEUED,
        input_message=message.message,
        source="dashboard",
    )
    session.add(task_db)
    await session.commit()

    # Push to queue
    await redis_client.push_task(task_id)
    await redis_client.add_session_task(session_id, task_id)

    logger.info("Chat message queued", task_id=task_id, session_id=session_id)

    return APIResponse(
        success=True,
        message="Task created",
        data={"task_id": task_id}
    )


@router.get("/agents")
async def list_agents():
    """List available sub-agents."""
    # TODO: Load from registry
    return [
        {
            "name": "planning",
            "agent_type": "planning",
            "description": "Analyzes bugs and creates fix plans",
            "is_builtin": True,
        },
        {
            "name": "executor",
            "agent_type": "executor",
            "description": "Implements code changes and fixes",
            "is_builtin": True,
        },
    ]


@router.get("/webhooks")
async def list_webhooks():
    """List configured webhooks."""
    # TODO: Load from registry
    return [
        {
            "name": "github",
            "endpoint": "/webhooks/github",
            "source": "github",
            "is_builtin": True,
        },
    ]
