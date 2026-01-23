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
from core.database.models import TaskDB, SessionDB, WebhookEventDB, WebhookConfigDB
from core.database.redis_client import redis_client
from core.webhook_configs import WEBHOOK_CONFIGS
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


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get task logs/output stream."""
    result = await db.execute(
        select(TaskDB).where(TaskDB.task_id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Try to get live output from Redis first (for running tasks)
    redis_output = await redis_client.get_output(task_id)
    
    return {
        "task_id": task.task_id,
        "status": task.status,
        "output": redis_output or task.output_stream or "",
        "error": task.error,
        "is_live": task.status == TaskStatus.RUNNING,
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
    conversation_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Send chat message to Brain with conversation context support."""
    from core.database.models import ConversationDB, ConversationMessageDB
    import json
    
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

    # Handle conversation context
    conversation = None
    conversation_context = ""
    
    if conversation_id:
        # Get existing conversation
        conv_result = await db.execute(
            select(ConversationDB).where(ConversationDB.conversation_id == conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        
        if conversation:
            # Get recent messages for context (last 20 messages)
            msg_result = await db.execute(
                select(ConversationMessageDB)
                .where(ConversationMessageDB.conversation_id == conversation_id)
                .order_by(ConversationMessageDB.created_at.desc())
                .limit(20)
            )
            recent_messages = list(reversed(msg_result.scalars().all()))
            
            if recent_messages:
                conversation_context = "\n\n## Previous Conversation Context:\n"
                for msg in recent_messages:
                    conversation_context += f"**{msg.role.capitalize()}**: {msg.content[:500]}\n"
                conversation_context += "\n## Current Message:\n"
    
    # Build input message with context
    full_input_message = conversation_context + message.message if conversation_context else message.message
    
    # Create task
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    task_db = TaskDB(
        task_id=task_id,
        session_id=session_id,
        user_id=session_db.user_id,
        assigned_agent="brain",
        agent_type=AgentType.PLANNING,
        status=TaskStatus.QUEUED,
        input_message=full_input_message,
        source="dashboard",
        source_metadata=json.dumps({
            "conversation_id": conversation_id,
            "has_context": bool(conversation_context)
        }) if conversation_id else "{}",
    )
    db.add(task_db)
    await db.commit()
    
    # Add user message to conversation
    if conversation:
        user_msg_id = f"msg-{uuid.uuid4().hex[:12]}"
        user_message = ConversationMessageDB(
            message_id=user_msg_id,
            conversation_id=conversation_id,
            role="user",
            content=message.message,
            task_id=task_id,
        )
        db.add(user_message)
        conversation.updated_at = datetime.utcnow()
        await db.commit()

    # Push to queue
    await redis_client.push_task(task_id)
    await redis_client.add_session_task(session_id, task_id)

    logger.info("Chat message queued", task_id=task_id, session_id=session_id, conversation_id=conversation_id)

    return APIResponse(
        success=True,
        message="Task created",
        data={
            "task_id": task_id,
            "conversation_id": conversation_id,
        }
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
async def list_webhooks(db: AsyncSession = Depends(get_db_session)):
    """List configured dynamic webhooks (from database only)."""
    # Get webhooks from database (dynamic webhooks only)
    result = await db.execute(select(WebhookConfigDB))
    webhooks = result.scalars().all()
    
    return [
        {
            "name": webhook.name,
            "provider": webhook.provider,
            "endpoint": webhook.endpoint,
            "is_builtin": False,
            "enabled": webhook.enabled,
        }
        for webhook in webhooks
    ]


@router.get("/webhooks/events")
async def list_webhook_events(
    db: AsyncSession = Depends(get_db_session),
    webhook_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """List recent webhook events."""
    query = select(WebhookEventDB).order_by(WebhookEventDB.created_at.desc()).limit(limit)
    
    if webhook_id:
        query = query.where(WebhookEventDB.webhook_id == webhook_id)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [
        {
            "event_id": event.event_id,
            "webhook_id": event.webhook_id,
            "provider": event.provider,
            "event_type": event.event_type,
            "task_id": event.task_id,
            "matched_command": event.matched_command,
            "response_sent": event.response_sent,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]


@router.get("/webhooks/events/{event_id}")
async def get_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed webhook event logs including payload."""
    result = await db.execute(
        select(WebhookEventDB).where(WebhookEventDB.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    return {
        "event_id": event.event_id,
        "webhook_id": event.webhook_id,
        "provider": event.provider,
        "event_type": event.event_type,
        "payload": event.payload_json,
        "matched_command": event.matched_command,
        "task_id": event.task_id,
        "response_sent": event.response_sent,
        "created_at": event.created_at.isoformat(),
    }


@router.get("/webhooks/stats")
async def get_webhook_stats(db: AsyncSession = Depends(get_db_session)):
    """Get webhook statistics."""
    import os
    
    # Count total webhooks from database
    total_query = select(func.count()).select_from(WebhookConfigDB)
    db_total = (await db.execute(total_query)).scalar() or 0
    
    # Count active webhooks from database
    active_query = select(func.count()).select_from(WebhookConfigDB).where(WebhookConfigDB.enabled == True)
    db_active = (await db.execute(active_query)).scalar() or 0
    
    # Count events by webhook name (for matching with static webhooks)
    events_query = select(
        WebhookEventDB.provider,
        func.count(WebhookEventDB.event_id).label("count")
    ).group_by(WebhookEventDB.provider)
    events_result = await db.execute(events_query)
    events_by_provider = {row[0]: row[1] for row in events_result}
    
    # Also get events by webhook_id for database webhooks
    events_by_id_query = select(
        WebhookEventDB.webhook_id,
        func.count(WebhookEventDB.event_id).label("count")
    ).group_by(WebhookEventDB.webhook_id)
    events_by_id_result = await db.execute(events_by_id_query)
    events_by_webhook = {row[0]: row[1] for row in events_by_id_result}
    
    # Add static webhook names to events_by_webhook for frontend compatibility
    # Count active static webhooks (those with secrets configured)
    static_active_count = 0
    for config in WEBHOOK_CONFIGS:
        if config.source in events_by_provider:
            events_by_webhook[config.name] = events_by_provider[config.source]
        
        # Check if static webhook is active (has secret if required)
        is_active = True
        if config.requires_signature and config.secret_env_var:
            secret_value = os.getenv(config.secret_env_var)
            is_active = bool(secret_value)
        
        if is_active:
            static_active_count += 1
    
    # Add static webhooks to totals
    static_count = len(WEBHOOK_CONFIGS)
    total = db_total + static_count
    active = db_active + static_active_count  # Only count active static webhooks
    
    return {
        "total_webhooks": total,
        "active_webhooks": active,
        "events_by_webhook": events_by_webhook,
    }
