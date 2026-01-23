"""
Slack Webhook Handler
Complete implementation: route + all supporting functions
Handles all Slack events
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
from core.webhook_configs import SLACK_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()
router = APIRouter()


# ✅ Verification function (Slack webhook ONLY)
async def verify_slack_signature(request: Request, body: bytes) -> None:
    """Verify Slack webhook signature ONLY."""
    secret = os.getenv("SLACK_WEBHOOK_SECRET")
    if not secret:
        logger.warning("SLACK_WEBHOOK_SECRET not configured, skipping verification")
        return
    
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    
    # Check timestamp (prevent replay attacks)
    import time
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=401, detail="Request timestamp too old")
    
    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected_signature = "v0=" + hmac.new(
        secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


# ✅ Immediate response function (Slack webhook ONLY)
async def send_slack_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response for Slack webhook ONLY."""
    try:
        # Slack challenge/verification
        if payload.get("type") == "url_verification":
            return True
        
        # Send ephemeral message
        event = payload.get("event", {})
        channel = event.get("channel")
        user = event.get("user")
        text = event.get("text", "")
        
        if channel and user:
            slack_token = os.getenv("SLACK_BOT_TOKEN")
            if slack_token:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postEphemeral",
                        headers={
                            "Authorization": f"Bearer {slack_token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "channel": channel,
                            "user": user,
                            "text": "👀 I received your request. Processing now..."
                        },
                        timeout=10.0
                    )
                logger.info("slack_ephemeral_sent", channel=channel, user=user)
                return True
        
        return False
        
    except Exception as e:
        logger.error("slack_immediate_response_error", error=str(e))
        return False


# ✅ Command matching function (Slack webhook ONLY)
def match_slack_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match command for Slack webhook ONLY. Handles all Slack event types."""
    # Extract text from event
    event = payload.get("event", {})
    text = event.get("text", "")
    
    if not text:
        # Use default command
        for cmd in SLACK_WEBHOOK.commands:
            if cmd.name == SLACK_WEBHOOK.default_command:
                return cmd
        return SLACK_WEBHOOK.commands[0] if SLACK_WEBHOOK.commands else None
    
    # Check prefix
    prefix = SLACK_WEBHOOK.command_prefix.lower()
    text_lower = text.lower()
    
    if prefix not in text_lower:
        # Use default command
        for cmd in SLACK_WEBHOOK.commands:
            if cmd.name == SLACK_WEBHOOK.default_command:
                return cmd
        return SLACK_WEBHOOK.commands[0] if SLACK_WEBHOOK.commands else None
    
    # Find command by name or alias
    for cmd in SLACK_WEBHOOK.commands:
        if cmd.name.lower() in text_lower:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() in text_lower:
                return cmd
    
    # Fallback to default
    for cmd in SLACK_WEBHOOK.commands:
        if cmd.name == SLACK_WEBHOOK.default_command:
            return cmd
    
    return SLACK_WEBHOOK.commands[0] if SLACK_WEBHOOK.commands else None


# ✅ Task creation function (Slack webhook ONLY)
async def create_slack_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession
) -> str:
    """Create task for Slack webhook ONLY. Handles all Slack event types."""
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
            "webhook_source": "slack",
            "webhook_name": SLACK_WEBHOOK.name,
            "command": command.name,
            "payload": payload
        }),
    )
    db.add(task_db)
    await db.flush()  # Flush to get task_db.id if needed
    
    # Create conversation immediately when task is created
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("slack_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
    await db.commit()
    
    # Push to queue
    await redis_client.push_task(task_id)
    
    logger.info("slack_task_created", task_id=task_id, command=command.name)
    
    return task_id


# ✅ Route handler (Slack webhook - handles all Slack events)
@router.post("/slack")
async def slack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Dedicated handler for Slack webhook.
    Handles all Slack events.
    All logic and functions in this file.
    """
    channel = None
    task_id = None
    
    try:
        # 1. Read body
        try:
            body = await request.body()
        except Exception as e:
            logger.error("slack_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
        # 2. Verify signature
        try:
            await verify_slack_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("slack_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
        # 3. Parse payload
        try:
            payload = json.loads(body.decode())
            payload["provider"] = "slack"
        except json.JSONDecodeError as e:
            logger.error("slack_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("slack_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        # 4. Handle Slack URL verification
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}
        
        # Extract channel for logging
        event = payload.get("event", {})
        channel = event.get("channel", "unknown")
        
        # 5. Extract event type
        event_type = event.get("type", "unknown")
        
        logger.info("slack_webhook_received", event_type=event_type, channel=channel)
        
        # 6. Match command based on event type and payload
        try:
            command = match_slack_command(payload, event_type)
            if not command:
                logger.warning("slack_no_command_matched", event_type=event_type, channel=channel)
                return {"status": "received", "actions": 0, "message": "No command matched"}
        except Exception as e:
            logger.error("slack_command_matching_error", error=str(e), channel=channel)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        # 7. Send immediate response
        immediate_response_sent = False
        try:
            immediate_response_sent = await send_slack_immediate_response(payload, command, event_type)
        except Exception as e:
            logger.error("slack_immediate_response_error", error=str(e), channel=channel, command=command.name)
            # Don't fail the whole request if immediate response fails
        
        # 8. Create task
        try:
            task_id = await create_slack_task(command, payload, db)
            logger.info("slack_task_created_success", task_id=task_id, channel=channel)
        except Exception as e:
            logger.error("slack_task_creation_failed", error=str(e), error_type=type(e).__name__, channel=channel, command=command.name)
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
        
        # 9. Log event
        try:
            event_id = f"evt-{uuid.uuid4().hex[:12]}"
            event_db = WebhookEventDB(
                event_id=event_id,
                webhook_id=SLACK_WEBHOOK.name,
                provider="slack",
                event_type=event_type,
                payload_json=json.dumps(payload),
                matched_command=command.name,
                task_id=task_id,
                response_sent=immediate_response_sent,
                created_at=datetime.utcnow()
            )
            db.add(event_db)
            await db.commit()
            logger.info("slack_event_logged", event_id=event_id, task_id=task_id, channel=channel)
        except Exception as e:
            logger.error("slack_event_logging_failed", error=str(e), task_id=task_id, channel=channel)
            # Don't fail the whole request if event logging fails
        
        logger.info("slack_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, channel=channel)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "slack_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            channel=channel,
            task_id=task_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
