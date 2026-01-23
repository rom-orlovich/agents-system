"""
Sentry Webhook Handler
Complete implementation: route + all supporting functions
Handles all Sentry events
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime
from typing import Optional
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB, SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import SENTRY_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()
router = APIRouter()


# ✅ Verification function (Sentry webhook ONLY)
async def verify_sentry_signature(request: Request, body: bytes) -> None:
    """Verify Sentry webhook signature ONLY."""
    secret = os.getenv("SENTRY_WEBHOOK_SECRET")
    if not secret:
        logger.warning("SENTRY_WEBHOOK_SECRET not configured, skipping verification")
        return
    
    signature = request.headers.get("Sentry-Hook-Signature", "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    # Compute expected signature (Sentry uses HMAC-SHA256)
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


# ✅ Immediate response function (Sentry webhook ONLY)
async def send_sentry_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response for Sentry webhook ONLY."""
    try:
        # Sentry webhooks don't support immediate responses
        # Log the event instead
        event = payload.get("event", {})
        event_id = event.get("id", "unknown")
        
        logger.info(
            "sentry_webhook_received",
            event_id=event_id,
            event_type=event_type,
            command=command.name
        )
        
        # Return True to indicate we acknowledged the event
        return True
        
    except Exception as e:
        logger.error("sentry_immediate_response_error", error=str(e))
        return False


# ✅ Command matching function (Sentry webhook ONLY)
def match_sentry_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match command for Sentry webhook ONLY. Handles all Sentry event types."""
    # Sentry doesn't use command prefix - always use default command
    # or match based on event action
    
    action = payload.get("action", "")
    
    # Map actions to commands
    if "resolve" in action.lower() or "fix" in action.lower():
        for cmd in SENTRY_WEBHOOK.commands:
            if cmd.name == "fix-error":
                return cmd
    
    # Default to analyze-error
    for cmd in SENTRY_WEBHOOK.commands:
        if cmd.name == SENTRY_WEBHOOK.default_command:
            return cmd
    
    return SENTRY_WEBHOOK.commands[0] if SENTRY_WEBHOOK.commands else None


# ✅ Task creation function (Sentry webhook ONLY)
async def create_sentry_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession
) -> str:
    """Create task for Sentry webhook ONLY. Handles all Sentry event types."""
    # Render template
    message = render_template(command.prompt_template, payload)
    
    # Create webhook session if needed
    webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
    session_db = SessionDB(
        session_id=webhook_session_id,
        user_id="webhook-system",
        machine_id="claude-agent-001",
        connected_at=datetime.utcnow(),
    )
    db.add(session_db)
    
    # Map agent name to AgentType
    agent_type_map = {
        "planning": AgentType.PLANNING,
        "executor": AgentType.EXECUTOR,
        "brain": AgentType.PLANNING,  # Brain uses PLANNING type
    }
    agent_type = agent_type_map.get(command.target_agent, AgentType.PLANNING)
    
    # Create task
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    task_db = TaskDB(
        task_id=task_id,
        session_id=webhook_session_id,
        user_id="webhook-system",
        assigned_agent=command.target_agent,
        agent_type=agent_type,
        status=TaskStatus.QUEUED,
        input_message=message,
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "sentry",
            "webhook_name": SENTRY_WEBHOOK.name,
            "command": command.name,
            "payload": payload
        }),
    )
    db.add(task_db)
    await db.flush()  # Flush to get task_db.id if needed
    
    # Create conversation immediately when task is created
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("sentry_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
    await db.commit()
    
    # Push to queue
    await redis_client.push_task(task_id)
    
    logger.info("sentry_task_created", task_id=task_id, command=command.name)
    
    return task_id


# ✅ Route handler (Sentry webhook - handles all Sentry events)
@router.post("/sentry")
async def sentry_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dedicated handler for Sentry webhook.
    Handles all Sentry events.
    All logic and functions in this file.
    """
    try:
        # 1. Read body
        body = await request.body()
        
        # 2. Verify signature
        await verify_sentry_signature(request, body)
        
        # 3. Parse payload
        payload = json.loads(body.decode())
        payload["provider"] = "sentry"
        
        # 4. Extract event type
        action = payload.get("action", "unknown")
        event_type = f"sentry.{action}"
        
        logger.info("sentry_webhook_received", event_type=event_type)
        
        # 5. Match command based on event type and payload
        command = match_sentry_command(payload, event_type)
        if not command:
            return {"status": "received", "actions": 0, "message": "No command matched"}
        
        # 6. Send immediate response
        immediate_response_sent = await send_sentry_immediate_response(payload, command, event_type)
        
        # 7. Create task
        task_id = await create_sentry_task(command, payload, db)
        
        # 8. Log event
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=SENTRY_WEBHOOK.name,
            provider="sentry",
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=command.name,
            task_id=task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.utcnow()
        )
        db.add(event_db)
        await db.commit()
        
        logger.info("sentry_webhook_processed", task_id=task_id, command=command.name, event_type=event_type)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("sentry_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
