"""Dashboard API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
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
from core.config import settings
from shared import (
    TaskStatus,
    AgentType,
    APIResponse,
)
import structlog
import json

logger = structlog.get_logger()

router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str


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
    duration_seconds: Optional[float]
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


@router.get("/tasks")
async def list_tasks(
    db: AsyncSession = Depends(get_db_session),
    session_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50),
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
async def get_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get task details."""
    result = await db.execute(select(TaskDB).where(TaskDB.task_id == task_id))
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
async def get_task_logs(task_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get task logs/output stream."""
    result = await db.execute(select(TaskDB).where(TaskDB.task_id == task_id))
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
async def stop_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    """Stop a running task."""
    result = await db.execute(select(TaskDB).where(TaskDB.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
        return APIResponse(
            success=False, message=f"Cannot stop task in status: {task.status}"
        )

    # Update status
    task.status = TaskStatus.CANCELLED
    await db.commit()

    # Update Redis
    await redis_client.set_task_status(task_id, TaskStatus.CANCELLED)

    logger.info("Task stopped", task_id=task_id)

    return APIResponse(success=True, message="Task stopped successfully")


@router.post("/chat")
async def chat_with_brain(
    request: ChatRequest,
    session_id: str = Query(...),
    conversation_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Send chat message to Brain with conversation context support. Creates new conversation if conversation_id is not provided."""
    from core.database.models import ConversationDB, ConversationMessageDB
    import json

    result = await db.execute(
        select(SessionDB).where(SessionDB.session_id == session_id)
    )
    session_db = result.scalar_one_or_none()

    if not session_db:
        user_id = "default-user"
        active = True

        try:
            from core.config import settings
            from api.credentials import ClaudeCredentials
            import json

            creds_path = settings.credentials_path
            if creds_path.exists():
                creds_data = json.loads(creds_path.read_text())
                creds = ClaudeCredentials.from_dict(creds_data)
                user_id = creds.account_id

                if not user_id:
                    import hashlib

                    token_hash = hashlib.sha256(
                        creds.access_token.encode()
                    ).hexdigest()[:16]
                    user_id = f"user-{token_hash}"

                existing_sessions_result = await db.execute(
                    select(SessionDB)
                    .where(SessionDB.user_id == user_id)
                    .order_by(SessionDB.connected_at.desc())
                    .limit(1)
                )
                existing_session = existing_sessions_result.scalar_one_or_none()
                if existing_session:
                    active = existing_session.active
        except Exception:
            pass

        session_db = SessionDB(
            session_id=session_id,
            user_id=user_id,
            machine_id="claude-agent-001",
            connected_at=datetime.now(timezone.utc),
            active=active,
        )
        db.add(session_db)
        await db.commit()

    conversation = None
    conversation_context = ""
    task_history_context = ""

    if conversation_id:
        conv_result = await db.execute(
            select(ConversationDB).where(
                ConversationDB.conversation_id == conversation_id
            )
        )
        conversation = conv_result.scalar_one_or_none()

        if conversation:
            # Get previous messages
            msg_result = await db.execute(
                select(ConversationMessageDB)
                .where(ConversationMessageDB.conversation_id == conversation_id)
                .order_by(ConversationMessageDB.created_at.desc())
                .limit(50)
            )
            recent_messages = list(reversed(msg_result.scalars().all()))

            if recent_messages:
                conversation_context = "\n\n## Previous Conversation Context:\n"
                for msg in recent_messages:
                    # Use larger context window (10k chars) instead of 500
                    content_preview = msg.content[:10000]
                    if len(msg.content) > 10000:
                        content_preview += "... (truncated)"
                    conversation_context += (
                        f"**{msg.role.capitalize()}**: {content_preview}\n"
                    )
                conversation_context += "\n## Current Message:\n"

            # Get last 10 tasks for this conversation
            tasks_result = await db.execute(
                select(TaskDB)
                .where(
                    TaskDB.source_metadata.like(
                        f'%"conversation_id": "{conversation_id}"%'
                    )
                )
                .order_by(TaskDB.created_at.desc())
                .limit(10)
            )
            recent_tasks = list(reversed(tasks_result.scalars().all()))

            if recent_tasks:
                task_history_context = "\n\n## Recent Tasks in This Conversation:\n"
                for task in recent_tasks:
                    status_emoji = {
                        TaskStatus.COMPLETED: "✅",
                        TaskStatus.FAILED: "❌",
                        TaskStatus.RUNNING: "🔄",
                        TaskStatus.QUEUED: "⏳",
                        TaskStatus.CANCELLED: "🚫",
                    }.get(task.status, "❓")

                    task_summary = (
                        task.input_message[:200] + "..."
                        if len(task.input_message or "") > 200
                        else task.input_message or ""
                    )
                    task_result_preview = ""
                    if task.result:
                        task_result_preview = (
                            f" | Result: {task.result[:200]}..."
                            if len(task.result) > 200
                            else f" | Result: {task.result}"
                        )
                    elif task.error:
                        task_result_preview = f" | Error: {task.error[:100]}..."

                    task_history_context += f"- {status_emoji} **{task.task_id}** ({task.status}): {task_summary}{task_result_preview}\n"
                task_history_context += "\n"
    else:
        conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
        conversation_title = (
            request.message[:50] + "..."
            if len(request.message) > 50
            else request.message
        )

        conversation = ConversationDB(
            conversation_id=conversation_id,
            user_id=session_db.user_id,
            title=conversation_title,
            metadata_json=json.dumps(
                {"source": "dashboard", "created_from": "execute_chat"}
            ),
        )
        db.add(conversation)
        await db.commit()
        logger.info(
            "New conversation created for execute chat",
            conversation_id=conversation_id,
            session_id=session_id,
        )

    # Combine context: task history + conversation context + current message
    context_parts = []
    if task_history_context:
        context_parts.append(task_history_context)
    if conversation_context:
        context_parts.append(conversation_context)
    context_parts.append(request.message)

    full_input_message = "".join(context_parts)

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
        source_metadata=json.dumps(
            {
                "conversation_id": conversation_id,
                "has_context": bool(conversation_context),
                "has_task_history": bool(task_history_context),
            }
        ),
    )
    db.add(task_db)
    await db.commit()

    user_msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    user_message = ConversationMessageDB(
        message_id=user_msg_id,
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        task_id=task_id,
    )
    db.add(user_message)
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await redis_client.push_task(task_id)
    await redis_client.add_session_task(session_id, task_id)

    logger.info(
        "Chat message queued",
        task_id=task_id,
        session_id=session_id,
        conversation_id=conversation_id,
    )

    return APIResponse(
        success=True,
        message="Task created",
        data={
            "task_id": task_id,
            "conversation_id": conversation_id,
        },
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
    limit: int = Query(50, ge=1, le=200),
):
    """List recent webhook events."""
    query = (
        select(WebhookEventDB).order_by(WebhookEventDB.created_at.desc()).limit(limit)
    )

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
async def get_webhook_event(event_id: str, db: AsyncSession = Depends(get_db_session)):
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
    active_query = (
        select(func.count())
        .select_from(WebhookConfigDB)
        .where(WebhookConfigDB.enabled.is_(True))
    )
    db_active = (await db.execute(active_query)).scalar() or 0

    # Count events by webhook name (for matching with static webhooks)
    events_query = select(
        WebhookEventDB.provider, func.count(WebhookEventDB.event_id).label("count")
    ).group_by(WebhookEventDB.provider)
    events_result = await db.execute(events_query)
    events_by_provider = {row[0]: row[1] for row in events_result}

    # Also get events by webhook_id for database webhooks
    events_by_id_query = select(
        WebhookEventDB.webhook_id, func.count(WebhookEventDB.event_id).label("count")
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


# Task Log Endpoints


@router.get("/tasks/{task_id}/logs/metadata")
async def get_task_log_metadata(task_id: str):
    """Get task metadata.json."""
    try:
        log_dir = settings.task_logs_dir / task_id
        metadata_file = log_dir / "metadata.json"

        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail="Task logs not found")

        with open(metadata_file, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task logs not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid metadata format")
    except Exception as e:
        logger.error("get_metadata_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/input")
async def get_task_log_input(task_id: str):
    """Get task input (01-input.json)."""
    try:
        log_dir = settings.task_logs_dir / task_id
        input_file = log_dir / "01-input.json"

        if not input_file.exists():
            raise HTTPException(status_code=404, detail="Task input log not found")

        with open(input_file, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task input log not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid input format")
    except Exception as e:
        logger.error("get_input_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/user-inputs")
async def get_task_log_user_inputs(task_id: str):
    """Get user inputs (02-user-inputs.jsonl) as JSON array."""
    try:
        log_dir = settings.task_logs_dir / task_id
        user_inputs_file = log_dir / "02-user-inputs.jsonl"

        if not user_inputs_file.exists():
            return []

        inputs = []
        with open(user_inputs_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    inputs.append(json.loads(line))

        return inputs

    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        logger.error("user_inputs_parse_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Invalid user inputs format")
    except Exception as e:
        logger.error("get_user_inputs_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/webhook-flow")
async def get_task_log_webhook_flow(task_id: str):
    """Get webhook flow events (03-webhook-flow.jsonl) as JSON array."""
    try:
        log_dir = settings.task_logs_dir / task_id
        webhook_file = log_dir / "03-webhook-flow.jsonl"

        if not webhook_file.exists():
            raise HTTPException(status_code=404, detail="Webhook flow log not found")

        events = []
        with open(webhook_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        return events

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Webhook flow log not found")
    except json.JSONDecodeError as e:
        logger.error("webhook_flow_parse_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Invalid webhook flow format")
    except Exception as e:
        logger.error("get_webhook_flow_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/agent-output")
async def get_task_log_agent_output(task_id: str):
    """Get agent output (04-agent-output.jsonl) as JSON array."""
    try:
        log_dir = settings.task_logs_dir / task_id
        output_file = log_dir / "04-agent-output.jsonl"

        if not output_file.exists():
            raise HTTPException(status_code=404, detail="Agent output log not found")

        outputs = []
        with open(output_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    outputs.append(json.loads(line))

        return outputs

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Agent output log not found")
    except json.JSONDecodeError as e:
        logger.error("agent_output_parse_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Invalid agent output format")
    except Exception as e:
        logger.error("get_agent_output_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/final-result")
async def get_task_log_final_result(task_id: str):
    """Get final result (06-final-result.json)."""
    try:
        log_dir = settings.task_logs_dir / task_id
        result_file = log_dir / "06-final-result.json"

        if not result_file.exists():
            raise HTTPException(status_code=404, detail="Final result log not found")

        with open(result_file, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Final result log not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid result format")
    except Exception as e:
        logger.error("get_final_result_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/full")
async def get_task_logs_full(task_id: str):
    """Get all task logs in a single combined response."""
    try:
        log_dir = settings.task_logs_dir / task_id

        if not log_dir.exists():
            raise HTTPException(status_code=404, detail="Task logs not found")

        result = {}

        # Read metadata (required)
        metadata_file = log_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                result["metadata"] = json.load(f)

        # Read input (optional)
        input_file = log_dir / "01-input.json"
        if input_file.exists():
            with open(input_file, "r") as f:
                result["input"] = json.load(f)

        # Read user inputs (optional)
        user_inputs_file = log_dir / "02-user-inputs.jsonl"
        if user_inputs_file.exists():
            inputs = []
            with open(user_inputs_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        inputs.append(json.loads(line))
            result["user_inputs"] = inputs

        # Read webhook flow (optional)
        webhook_file = log_dir / "03-webhook-flow.jsonl"
        if webhook_file.exists():
            events = []
            with open(webhook_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
            result["webhook_flow"] = events

        # Read agent output (optional)
        output_file = log_dir / "04-agent-output.jsonl"
        if output_file.exists():
            outputs = []
            with open(output_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        outputs.append(json.loads(line))
            result["agent_output"] = outputs

        # Read knowledge interactions (optional)
        knowledge_file = log_dir / "05-knowledge-interactions.jsonl"
        if knowledge_file.exists():
            interactions = []
            with open(knowledge_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        interactions.append(json.loads(line))
            result["knowledge_interactions"] = interactions

        # Read final result (optional)
        result_file = log_dir / "06-final-result.json"
        if result_file.exists():
            with open(result_file, "r") as f:
                result["final_result"] = json.load(f)

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task logs not found")
    except json.JSONDecodeError as e:
        logger.error("full_logs_parse_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Invalid log format")
    except Exception as e:
        logger.error("get_full_logs_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/logs/knowledge-interactions")
async def get_task_log_knowledge_interactions(task_id: str):
    """Get knowledge interactions (05-knowledge-interactions.jsonl) as JSON array."""
    try:
        log_dir = settings.task_logs_dir / task_id
        knowledge_file = log_dir / "05-knowledge-interactions.jsonl"

        if not knowledge_file.exists():
            return []

        interactions = []
        with open(knowledge_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    interactions.append(json.loads(line))

        return interactions

    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        logger.error("knowledge_parse_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Invalid knowledge log format")
    except Exception as e:
        logger.error("get_knowledge_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/knowledge-summary")
async def get_task_knowledge_summary(task_id: str):
    """Get a summary of knowledge service usage for a task."""
    try:
        log_dir = settings.task_logs_dir / task_id
        knowledge_file = log_dir / "05-knowledge-interactions.jsonl"

        if not knowledge_file.exists():
            return {
                "task_id": task_id,
                "knowledge_enabled": False,
                "total_queries": 0,
                "total_results": 0,
                "tools_used": [],
                "source_types_queried": [],
                "total_query_time_ms": 0,
                "cache_hit_rate": 0,
            }

        interactions = []
        with open(knowledge_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    interactions.append(json.loads(line))

        queries = [i for i in interactions if i.get("type") == "query"]
        results = [i for i in interactions if i.get("type") == "result"]

        tools_used = list(set(i.get("tool_name") for i in interactions))
        source_types = []
        for q in queries:
            source_types.extend(q.get("source_types", []))
        source_types = list(set(source_types))

        total_results = sum(r.get("results_count", 0) for r in results)
        total_query_time = sum(r.get("query_time_ms", 0) for r in results)
        cached_count = sum(1 for r in results if r.get("cached"))
        cache_hit_rate = (cached_count / len(results) * 100) if results else 0

        return {
            "task_id": task_id,
            "knowledge_enabled": True,
            "total_queries": len(queries),
            "total_results": total_results,
            "tools_used": tools_used,
            "source_types_queried": source_types,
            "total_query_time_ms": round(total_query_time, 2),
            "cache_hit_rate": round(cache_hit_rate, 1),
            "interactions": interactions,
        }

    except Exception as e:
        logger.error("get_knowledge_summary_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
