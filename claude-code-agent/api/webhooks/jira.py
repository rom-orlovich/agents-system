"""
Jira Webhook Handler
Complete implementation: route + all supporting functions
Handles all Jira events
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
import httpx
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB, SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import JIRA_WEBHOOK
from core.webhook_engine import render_template
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()
router = APIRouter()


# ✅ Verification function (Jira webhook ONLY)
async def verify_jira_signature(request: Request, body: bytes) -> None:
    """Verify Jira webhook signature ONLY."""
    secret = os.getenv("JIRA_WEBHOOK_SECRET")
    if not secret:
        logger.warning("JIRA_WEBHOOK_SECRET not configured, skipping verification")
        return
    
    signature = request.headers.get("X-Jira-Signature", "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    # Compute expected signature (Jira uses HMAC-SHA256)
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


# ✅ Immediate response function (Jira webhook ONLY)
async def send_jira_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response for Jira webhook ONLY."""
    try:
        # Jira webhooks typically don't support immediate responses
        # Log the event instead
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "unknown")
        
        logger.info(
            "jira_webhook_received",
            issue_key=issue_key,
            event_type=event_type,
            command=command.name
        )
        
        # Return True to indicate we acknowledged the event
        return True
        
    except Exception as e:
        logger.error("jira_immediate_response_error", error=str(e))
        return False


# ✅ Command matching function (Jira webhook ONLY)
def match_jira_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match command for Jira webhook ONLY. Handles all Jira event types."""
    # Extract text from payload
    text = ""
    
    # Try to get comment body
    comment = payload.get("comment", {})
    if comment:
        text = comment.get("body", "")
    
    # If no comment, try issue description or summary
    if not text:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        text = fields.get("description", "") or fields.get("summary", "")
    
    if not text:
        # Use default command
        for cmd in JIRA_WEBHOOK.commands:
            if cmd.name == JIRA_WEBHOOK.default_command:
                return cmd
        return JIRA_WEBHOOK.commands[0] if JIRA_WEBHOOK.commands else None
    
    # Check prefix
    prefix = JIRA_WEBHOOK.command_prefix.lower()
    text_lower = text.lower()
    
    if prefix not in text_lower:
        # Use default command
        for cmd in JIRA_WEBHOOK.commands:
            if cmd.name == JIRA_WEBHOOK.default_command:
                return cmd
        return JIRA_WEBHOOK.commands[0] if JIRA_WEBHOOK.commands else None
    
    # Find command by name or alias
    for cmd in JIRA_WEBHOOK.commands:
        if cmd.name.lower() in text_lower:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() in text_lower:
                return cmd
    
    # Fallback to default
    for cmd in JIRA_WEBHOOK.commands:
        if cmd.name == JIRA_WEBHOOK.default_command:
            return cmd
    
    return JIRA_WEBHOOK.commands[0] if JIRA_WEBHOOK.commands else None


# ✅ Task creation function (Jira webhook ONLY)
async def create_jira_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession
) -> str:
    """Create task for Jira webhook ONLY. Handles all Jira event types."""
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
            "webhook_source": "jira",
            "webhook_name": JIRA_WEBHOOK.name,
            "command": command.name,
            "payload": payload
        }),
    )
    db.add(task_db)
    await db.commit()
    
    # Push to queue
    await redis_client.push_task(task_id)
    
    logger.info("jira_task_created", task_id=task_id, command=command.name)
    
    return task_id


# ✅ Route handler (Jira webhook - handles all Jira events)
@router.post("/jira")
async def jira_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dedicated handler for Jira webhook.
    Handles all Jira events.
    All logic and functions in this file.
    """
    try:
        # 1. Read body
        body = await request.body()
        
        # 2. Verify signature
        await verify_jira_signature(request, body)
        
        # 3. Parse payload
        payload = json.loads(body.decode())
        payload["provider"] = "jira"
        
        # 4. Extract event type
        event_type = payload.get("webhookEvent", "unknown")
        
        logger.info("jira_webhook_received", event_type=event_type)
        
        # 5. Match command based on event type and payload
        command = match_jira_command(payload, event_type)
        if not command:
            return {"status": "received", "actions": 0, "message": "No command matched"}
        
        # 6. Send immediate response
        immediate_response_sent = await send_jira_immediate_response(payload, command, event_type)
        
        # 7. Create task
        task_id = await create_jira_task(command, payload, db)
        
        # 8. Log event
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=JIRA_WEBHOOK.name,
            provider="jira",
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=command.name,
            task_id=task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.utcnow()
        )
        db.add(event_db)
        await db.commit()
        
        logger.info("jira_webhook_processed", task_id=task_id, command=command.name, event_type=event_type)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("jira_webhook_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
