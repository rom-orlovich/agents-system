"""Dashboard API endpoints."""

from datetime import datetime
from typing import List, Optional, Annotated
import uuid
import math

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_session as get_db_session
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


class TaskTableRow(BaseModel):
    """Task table row response."""
    task_id: str
    session_id: str
    status: str
    assigned_agent: Optional[str]
    agent_type: str
    created_at: str
    completed_at: Optional[str]
    cost_usd: float
    duration_seconds: Optional[int]
    input_message: str
    
    @classmethod
    def from_db(cls, task: TaskDB) -> "TaskTableRow":
        """Create from database model."""
        return cls(
            task_id=task.task_id,
            session_id=task.session_id,
            status=task.status,
            assigned_agent=task.assigned_agent,
            agent_type=task.agent_type,
            created_at=task.created_at.isoformat(),
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            cost_usd=task.cost_usd or 0.0,
            duration_seconds=task.duration_seconds,
            input_message=task.input_message[:200] if task.input_message else "",
        )


class TaskTableResponse(BaseModel):
    """Task table response with pagination."""
    tasks: List[TaskTableRow]
    total: int
    page: int
    page_size: int
    total_pages: int


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
async def get_session_by_id(
    session_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get session details."""
    result = await db.execute(
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
    db: AsyncSession = Depends(get_db_session),
    session_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50)
):
    """List tasks with optional filters."""
    query = select(TaskDB).order_by(TaskDB.created_at.desc()).limit(limit)

    if session_id:
        query = query.where(TaskDB.session_id == session_id)
    if status:
        query = query.where(TaskDB.status == status)

    result = await db.execute(query)
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


@router.get("/tasks/table")
async def list_tasks_table(
    db: AsyncSession = Depends(get_db_session),
    session_id: str | None = Query(None),
    status: str | None = Query(None),
    subagent: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TaskTableResponse:
    """List tasks with pagination and sorting for table view."""
    query = select(TaskDB)
    
    # Apply filters
    if session_id:
        query = query.where(TaskDB.session_id == session_id)
    if status:
        query = query.where(TaskDB.status == status)
    if subagent:
        query = query.where(TaskDB.assigned_agent == subagent)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Apply sorting
    sort_column = getattr(TaskDB, sort_by, TaskDB.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return TaskTableResponse(
        tasks=[TaskTableRow.from_db(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get task details."""
    result = await db.execute(
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
    db: AsyncSession = Depends(get_db_session)
):
    """Stop a running task."""
    result = await db.execute(
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
    await db.commit()

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
    db: AsyncSession = Depends(get_db_session)
):
    """Send chat message to Brain."""
    # Create or get session
    result = await db.execute(
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
        db.add(session_db)
        await db.commit()

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
    db.add(task_db)
    await db.commit()

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
