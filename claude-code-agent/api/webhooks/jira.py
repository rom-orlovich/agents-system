from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
import httpx
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB, SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import JIRA_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from core.routing_metadata import extract_jira_metadata
import base64
import httpx
from core.config import settings
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()
router = APIRouter()


async def verify_jira_signature(request: Request, body: bytes) -> None:
    signature = request.headers.get("X-Jira-Signature", "")
    secret = os.getenv("JIRA_WEBHOOK_SECRET") or settings.jira_webhook_secret
    
    if signature:
        if not secret:
            raise HTTPException(status_code=401, detail="Webhook secret not configured but signature provided")
        
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    elif secret:
        logger.warning("JIRA_WEBHOOK_SECRET configured but no signature header provided")


def is_assignee_changed_to_ai(payload: dict, event_type: str) -> bool:
    from core.config import settings
    
    ai_agent_name = settings.jira_ai_agent_name or os.getenv("JIRA_AI_AGENT_NAME", "AI Agent")
    
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
    
    if event_type in ["jira:issue_created", "issue_created"]:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        if assignee:
            assignee_name = assignee.get("displayName", "") or assignee.get("name", "")
            if assignee_name and ai_agent_name.lower() in assignee_name.lower():
                issue_key = issue.get("key", "unknown")
                logger.info("jira_issue_created_with_ai_assignee", issue_key=issue_key, assignee=assignee_name)
                return True
    
    return False


def generate_jira_immediate_message(command: WebhookCommand) -> str:
    if command.name == "analyze":
        return "👀 AI Agent: I'll analyze this issue and provide insights shortly."
    elif command.name == "plan":
        return "📋 AI Agent: Creating a plan to resolve this issue..."
    elif command.name == "fix":
        return "🔧 AI Agent: Starting to implement a fix for this issue..."
    else:
        return f"🤖 AI Agent: Processing '{command.name}' command..."


async def send_jira_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    try:
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "unknown")
        
        logger.info(
            "jira_webhook_received",
            issue_key=issue_key,
            event_type=event_type,
            command=command.name
        )
        
        if not is_assignee_changed_to_ai(payload, event_type):
            logger.debug(
                "jira_immediate_comment_skipped",
                issue_key=issue_key,
                event_type=event_type
            )
            return False
        
        if issue_key == "unknown":
            return False
        
        message = generate_jira_immediate_message(command)
        await post_jira_comment(payload, message)
        logger.info("jira_immediate_comment_sent", issue_key=issue_key, command=command.name)
        return True
        
    except Exception as e:
        logger.error("jira_immediate_response_error", error=str(e))
        return False


def match_jira_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    text = ""
    
    comment = payload.get("comment", {})
    if comment:
        text = comment.get("body", "")
    
    if not text:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        text = fields.get("description", "") or fields.get("summary", "")
    
    if not text:
        for cmd in JIRA_WEBHOOK.commands:
            if cmd.name == JIRA_WEBHOOK.default_command:
                return cmd
        return JIRA_WEBHOOK.commands[0] if JIRA_WEBHOOK.commands else None
    
    prefix = JIRA_WEBHOOK.command_prefix.lower()
    text_lower = text.lower()
    
    if prefix not in text_lower:
        for cmd in JIRA_WEBHOOK.commands:
            if cmd.name == JIRA_WEBHOOK.default_command:
                return cmd
        return JIRA_WEBHOOK.commands[0] if JIRA_WEBHOOK.commands else None
    
    for cmd in JIRA_WEBHOOK.commands:
        if cmd.name.lower() in text_lower:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() in text_lower:
                return cmd
    
    for cmd in JIRA_WEBHOOK.commands:
        if cmd.name == JIRA_WEBHOOK.default_command:
            return cmd
    
    return JIRA_WEBHOOK.commands[0] if JIRA_WEBHOOK.commands else None


async def create_jira_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession
) -> str:
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    
    base_message = render_template(command.prompt_template, payload, task_id=task_id)
    
    from core.webhook_engine import wrap_prompt_with_brain_instructions
    message = wrap_prompt_with_brain_instructions(base_message, task_id=task_id)
    
    webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
    session_db = SessionDB(
        session_id=webhook_session_id,
        user_id="webhook-system",
        machine_id="claude-agent-001",
        connected_at=datetime.now(timezone.utc),
    )
    db.add(session_db)
    
    agent_type_map = {
        "planning": AgentType.PLANNING,
        "executor": AgentType.EXECUTOR,
        "brain": AgentType.PLANNING,
    }
    agent_type = agent_type_map.get("brain", AgentType.PLANNING)
    
    # Extract clean routing metadata for response posting
    routing = extract_jira_metadata(payload)

    task_db = TaskDB(
        task_id=task_id,
        session_id=webhook_session_id,
        user_id="webhook-system",
        assigned_agent="brain",
        agent_type=agent_type,
        status=TaskStatus.QUEUED,
        input_message=message,
        source="webhook",
        source_metadata=json.dumps({
            "webhook_source": "jira",
            "webhook_name": JIRA_WEBHOOK.name,
            "command": command.name,
            "original_target_agent": command.target_agent,
            "routing": routing,  # Clean routing info for response posting
            "payload": payload
        }),
    )
    db.add(task_db)
    await db.flush()
    
    from core.webhook_engine import generate_external_id, generate_flow_id
    external_id = generate_external_id("jira", payload)
    flow_id = generate_flow_id(external_id)
    
    source_metadata = json.loads(task_db.source_metadata or "{}")
    source_metadata["flow_id"] = flow_id
    source_metadata["external_id"] = external_id
    task_db.source_metadata = json.dumps(source_metadata)
    task_db.flow_id = flow_id
    
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("jira_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
    try:
        from core.claude_tasks_sync import sync_task_to_claude_tasks
        claude_task_id = sync_task_to_claude_tasks(
            task_db=task_db,
            flow_id=flow_id,
            conversation_id=conversation_id
        )
        if claude_task_id:
            source_metadata = json.loads(task_db.source_metadata or "{}")
            source_metadata["claude_task_id"] = claude_task_id
            task_db.source_metadata = json.dumps(source_metadata)
    except Exception as sync_error:
        logger.warning(
            "jira_claude_tasks_sync_failed",
            task_id=task_id,
            error=str(sync_error)
        )
    
    await db.commit()
    
    logger.info("jira_task_saved_to_db", task_id=task_id, session_id=webhook_session_id, agent=command.target_agent)
    
    try:
        await redis_client.push_task(task_id)
        logger.info("jira_task_pushed_to_queue", task_id=task_id)
    except Exception as e:
        logger.error("jira_task_queue_push_failed", task_id=task_id, error=str(e))
        raise
    
    try:
        await redis_client.add_session_task(webhook_session_id, task_id)
        logger.info("jira_task_added_to_session", task_id=task_id, session_id=webhook_session_id)
    except Exception as e:
        logger.warning("jira_session_task_add_failed", task_id=task_id, error=str(e))
    
    logger.info("jira_task_created", task_id=task_id, command=command.name, message_preview=message[:100])
    
    return task_id


async def post_jira_comment(payload: dict, message: str):
    try:
        from core.config import settings
        import os
        
        jira_url = os.getenv("JIRA_URL") or settings.jira_url
        jira_email = os.getenv("JIRA_EMAIL") or settings.jira_email
        jira_api_token = os.getenv("JIRA_API_TOKEN") or settings.jira_api_token
        
        if not jira_url or not jira_api_token or not jira_email:
            logger.warning("jira_credentials_missing", message="Jira API credentials not configured")
            return
        
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        
        if not issue_key:
            logger.warning("jira_issue_key_missing", payload_keys=list(payload.keys()))
            return
        
        api_url = f"{jira_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment"
        
        auth_string = f"{jira_email}:{jira_api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": message
                                    }
                                ]
                            }
                        ]
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            logger.info(
                "jira_comment_posted",
                issue_key=issue_key,
                comment_id=response.json().get("id")
            )
            
    except httpx.HTTPStatusError as e:
        logger.error(
            "jira_comment_failed",
            status_code=e.response.status_code,
            error=str(e),
            response_text=e.response.text[:500] if e.response.text else None
        )
    except Exception as e:
        logger.error("jira_api_error", error=str(e), error_type=type(e).__name__)


@router.post("/jira")
async def jira_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    issue_key = None
    task_id = None
    
    try:
        try:
            body = await request.body()
        except Exception as e:
            logger.error("jira_webhook_body_read_failed", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
        
        try:
            await verify_jira_signature(request, body)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("jira_signature_verification_error", error=str(e))
            raise HTTPException(status_code=401, detail=f"Signature verification failed: {str(e)}")
        
        try:
            payload = json.loads(body.decode())
            payload["provider"] = "jira"
        except json.JSONDecodeError as e:
            logger.error("jira_payload_parse_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        except Exception as e:
            logger.error("jira_payload_decode_error", error=str(e))
            raise HTTPException(status_code=400, detail=f"Failed to decode payload: {str(e)}")
        
        issue_key = payload.get("issue", {}).get("key", "unknown")
        
        event_type = payload.get("webhookEvent", "unknown")
        
        logger.info("jira_webhook_received", event_type=event_type, issue_key=issue_key, payload_keys=list(payload.keys()))
        
        if not is_assignee_changed_to_ai(payload, event_type):
            logger.info(
                "jira_webhook_skipped_no_ai_assignee",
                event_type=event_type,
                issue_key=issue_key,
                message="Assignee not changed to AI Agent, skipping webhook processing"
            )
            return {
                "status": "skipped",
                "message": "Assignee not changed to AI Agent",
                "issue_key": issue_key
            }
        
        try:
            command = match_jira_command(payload, event_type)
            if not command:
                logger.warning("jira_no_command_matched", event_type=event_type, issue_key=issue_key, payload_sample=str(payload)[:500])
                if JIRA_WEBHOOK.commands:
                    command = JIRA_WEBHOOK.commands[0]
                    logger.info("jira_using_fallback_command", command=command.name, issue_key=issue_key)
                else:
                    return {"status": "received", "actions": 0, "message": "No commands configured"}
        except Exception as e:
            logger.error("jira_command_matching_error", error=str(e), issue_key=issue_key)
            raise HTTPException(status_code=500, detail=f"Command matching failed: {str(e)}")
        
        logger.info("jira_command_matched", command=command.name, event_type=event_type, issue_key=issue_key)
        
        immediate_response_sent = False
        try:
            immediate_response_sent = await send_jira_immediate_response(payload, command, event_type)
        except Exception as e:
            logger.error("jira_immediate_response_error", error=str(e), issue_key=issue_key, command=command.name)
        
        try:
            task_id = await create_jira_task(command, payload, db)
            logger.info("jira_task_created_success", task_id=task_id, issue_key=issue_key)
        except Exception as e:
            logger.error("jira_task_creation_failed", error=str(e), error_type=type(e).__name__, issue_key=issue_key, command=command.name)
            raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")
        
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
                created_at=datetime.now(timezone.utc)
            )
            db.add(event_db)
            await db.commit()
            logger.info("jira_event_logged", event_id=event_id, task_id=task_id, issue_key=issue_key)
        except Exception as e:
            logger.error("jira_event_logging_failed", error=str(e), task_id=task_id, issue_key=issue_key)
        
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
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "issue_key": issue_key
        }
