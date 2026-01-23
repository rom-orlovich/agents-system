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
from core.webhook_engine import render_template, create_webhook_conversation
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


# ✅ Helper function: Check if assignee changed to AI Agent
def is_assignee_changed_to_ai(payload: dict, event_type: str) -> bool:
    """Check if assignee was changed to AI Agent."""
    from core.config import settings
    
    ai_agent_name = settings.jira_ai_agent_name or os.getenv("JIRA_AI_AGENT_NAME", "AI Agent")
    
    # Check changelog for assignee changes
    changelog = payload.get("changelog", {})
    if changelog:
        items = changelog.get("items", [])
        for item in items:
            if item.get("field") == "assignee":
                to_value = item.get("toString", "")
                if to_value and ai_agent_name.lower() in to_value.lower():
                    issue_key = payload.get("issue", {}).get("key", "unknown")
                    logger.info("jira_assignee_changed_to_ai", issue_key=issue_key, new_assignee=to_value)
                    return True
    
    # Check current assignee if changelog doesn't show the change
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    assignee = fields.get("assignee")
    if assignee:
        assignee_name = assignee.get("displayName", "") or assignee.get("name", "")
        if assignee_name and ai_agent_name.lower() in assignee_name.lower():
            # Only for update events (not just reads)
            if event_type in ["jira:issue_updated", "issue_updated"]:
                issue_key = issue.get("key", "unknown")
                logger.info("jira_current_assignee_is_ai", issue_key=issue_key, assignee=assignee_name)
                return True
    
    return False


# ✅ Helper function: Generate immediate response message
def generate_jira_immediate_message(command: WebhookCommand) -> str:
    """Generate immediate response message based on command."""
    if command.name == "analyze":
        return "👀 AI Agent: I'll analyze this issue and provide insights shortly."
    elif command.name == "plan":
        return "📋 AI Agent: Creating a plan to resolve this issue..."
    elif command.name == "fix":
        return "🔧 AI Agent: Starting to implement a fix for this issue..."
    else:
        return f"🤖 AI Agent: Processing '{command.name}' command..."


# ✅ Immediate response function (Jira webhook ONLY)
async def send_jira_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response for Jira webhook ONLY. Only posts if assignee changed to AI Agent."""
    try:
        from core.webhook_engine import jira_post_comment
        
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "unknown")
        
        logger.info(
            "jira_webhook_received",
            issue_key=issue_key,
            event_type=event_type,
            command=command.name
        )
        
        # Check if assignee was changed to AI Agent
        if not is_assignee_changed_to_ai(payload, event_type):
            logger.debug(
                "jira_immediate_comment_skipped",
                issue_key=issue_key,
                event_type=event_type
            )
            return False
        
        # Only post comment if assignee was changed to AI Agent
        if issue_key == "unknown":
            return False
        
        # Generate and post message
        message = generate_jira_immediate_message(command)
        await jira_post_comment(payload, message)
        logger.info("jira_immediate_comment_sent", issue_key=issue_key, command=command.name)
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
    await db.flush()  # Flush to get task_db.id if needed
    
    # Create conversation immediately when task is created
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("jira_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
    await db.commit()
    
    logger.info("jira_task_saved_to_db", task_id=task_id, session_id=webhook_session_id, agent=command.target_agent)
    
    # Push to queue
    try:
        await redis_client.push_task(task_id)
        logger.info("jira_task_pushed_to_queue", task_id=task_id)
    except Exception as e:
        logger.error("jira_task_queue_push_failed", task_id=task_id, error=str(e))
        raise
    
    # Add task to session
    try:
        await redis_client.add_session_task(webhook_session_id, task_id)
        logger.info("jira_task_added_to_session", task_id=task_id, session_id=webhook_session_id)
    except Exception as e:
        logger.warning("jira_session_task_add_failed", task_id=task_id, error=str(e))
        # Don't fail if this doesn't work
    
    logger.info("jira_task_created", task_id=task_id, command=command.name, message_preview=message[:100])
    
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
    issue_key = None
    task_id = None
    
    try:
        # 1. Read body
        try:
            body = await request.body()
        except Exception as e:
            logger.error("jira_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
        # 2. Verify signature
        try:
            await verify_jira_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("jira_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
        # 3. Parse payload
        try:
            payload = json.loads(body.decode())
            payload["provider"] = "jira"
        except json.JSONDecodeError as e:
            logger.error("jira_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("jira_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        # Extract issue key for logging
        issue_key = payload.get("issue", {}).get("key", "unknown")
        
        # 4. Extract event type
        event_type = payload.get("webhookEvent", "unknown")
        
        logger.info("jira_webhook_received", event_type=event_type, issue_key=issue_key, payload_keys=list(payload.keys()))
        
        # 5. Match command based on event type and payload
        try:
            command = match_jira_command(payload, event_type)
            if not command:
                logger.warning("jira_no_command_matched", event_type=event_type, issue_key=issue_key, payload_sample=str(payload)[:500])
                # Still create a task with default command
                if JIRA_WEBHOOK.commands:
                    command = JIRA_WEBHOOK.commands[0]  # Use first command as fallback
                    logger.info("jira_using_fallback_command", command=command.name, issue_key=issue_key)
                else:
                    return {"status": "received", "actions": 0, "message": "No commands configured"}
        except Exception as e:
            logger.error("jira_command_matching_error", error=str(e), issue_key=issue_key)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        logger.info("jira_command_matched", command=command.name, event_type=event_type, issue_key=issue_key)
        
        # 6. Send immediate response
        immediate_response_sent = False
        try:
            immediate_response_sent = await send_jira_immediate_response(payload, command, event_type)
        except Exception as e:
            logger.error("jira_immediate_response_error", error=str(e), issue_key=issue_key, command=command.name)
            # Don't fail the whole request if immediate response fails
        
        # 7. Create task
        try:
            task_id = await create_jira_task(command, payload, db)
            logger.info("jira_task_created_success", task_id=task_id, issue_key=issue_key)
        except Exception as e:
            logger.error("jira_task_creation_failed", error=str(e), error_type=type(e).__name__, issue_key=issue_key, command=command.name)
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
        
        # 8. Log event
        try:
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
            logger.info("jira_event_logged", event_id=event_id, task_id=task_id, issue_key=issue_key)
        except Exception as e:
            logger.error("jira_event_logging_failed", error=str(e), task_id=task_id, issue_key=issue_key)
            # Don't fail the whole request if event logging fails
        
        logger.info("jira_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, issue_key=issue_key)
        
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
            "jira_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            issue_key=issue_key,
            task_id=task_id,
            exc_info=True
        )
        # Return error details for debugging
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "issue_key": issue_key
        }
