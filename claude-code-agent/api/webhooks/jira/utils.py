"""
Jira webhook utility functions.
Signature verification, command matching, task creation, and immediate responses.
"""

import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
import structlog

from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database.models import SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import JIRA_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from core.jira_client import jira_client
from core.routing_metadata import extract_jira_metadata
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()


async def verify_jira_signature(request: Request, body: bytes) -> None:
    """Verify Jira webhook signature."""
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
    """Check if assignee was changed to AI agent."""
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
    """Generate immediate response message for Jira."""
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
    """Send immediate response to Jira."""
    try:
        issue = payload.get("issue", {})
        issue_key = issue.get("key", "unknown")
        
        logger.info(
            "jira_webhook_received",
            issue_key=issue_key,
            event_type=event_type,
            command=command.name
        )
        
        has_assignee_change = is_assignee_changed_to_ai(payload, event_type)
        has_comment_with_agent = bool(payload.get("comment", {}).get("body", ""))
        
        if not has_assignee_change and not has_comment_with_agent:
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
    """Match Jira webhook payload to a command."""
    from core.command_matcher import extract_command

    comment = payload.get("comment", {})
    author = comment.get("author", {})
    author_type = author.get("accountType", "")
    author_name = author.get("displayName", "")

    if author_type == "app" or "bot" in author_name.lower():
        logger.info("jira_skipped_bot_comment", author=author_name, author_type=author_type)
        return None

    text = ""
    is_comment_event = bool(comment)

    if comment:
        text = comment.get("body", "")

    if not text:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        text = fields.get("description", "") or fields.get("summary", "")

    if is_assignee_changed_to_ai(payload, event_type):
        for cmd in JIRA_WEBHOOK.commands:
            if cmd.name == JIRA_WEBHOOK.default_command:
                payload["_user_content"] = ""
                return cmd
        logger.warning("jira_default_command_not_found", default_command=JIRA_WEBHOOK.default_command)
        return None

    result = extract_command(text)
    if result is None:
        logger.debug("jira_no_agent_command", text_preview=text[:100] if text else "", is_comment=is_comment_event)
        return None

    command_name, user_content = result
    payload["_user_content"] = user_content

    for cmd in JIRA_WEBHOOK.commands:
        if cmd.name.lower() == command_name:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() == command_name:
                return cmd

    logger.warning("jira_command_not_configured", command=command_name)
    return None


async def create_jira_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession,
    completion_handler: str
) -> str:
    """Create a task from Jira webhook."""
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
            "routing": routing,
            "payload": payload,
            "completion_handler": completion_handler
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
    """Post a comment to a Jira issue."""
    try:
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        
        if not issue_key:
            logger.warning("jira_issue_key_missing", payload_keys=list(payload.keys()))
            return
        
        await jira_client.post_comment(issue_key, message)
            
    except ValueError as e:
        logger.warning("jira_client_not_configured", error=str(e))
    except Exception as e:
        logger.error("jira_comment_post_failed", issue_key=issue_key, error=str(e), error_type=type(e).__name__)


async def post_jira_task_comment(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0
) -> bool:
    """Post a comment to Jira after task completion."""
    try:
        issue = payload.get("issue", {})
        issue_key = issue.get("key")
        
        if not issue_key:
            logger.warning("jira_post_task_comment_no_issue_key", payload_keys=list(payload.keys()))
            return False
        
        if success:
            formatted_message = f"{message}"
        else:
            formatted_message = f"{message}"
        
        max_length = 8000
        if len(formatted_message) > max_length:
            truncated_message = formatted_message[:max_length]
            last_period = truncated_message.rfind(".")
            last_newline = truncated_message.rfind("\n")
            truncate_at = max(last_period, last_newline)
            if truncate_at > max_length * 0.8:
                truncated_message = truncated_message[:truncate_at + 1]
            formatted_message = truncated_message + "\n\n... (message truncated)"
        
        if success and cost_usd > 0:
            formatted_message += f"\n\n💰 Cost: ${cost_usd:.4f}"
        
        await jira_client.post_comment(issue_key, formatted_message)
        logger.info("jira_task_comment_posted", issue_key=issue_key)
        return True
        
    except Exception as e:
        logger.error("jira_post_task_comment_error", error=str(e))
        return False


async def send_slack_notification(
    task_id: str,
    webhook_source: str,
    command: str,
    success: bool,
    result: Optional[str] = None,
    error: Optional[str] = None
) -> bool:
    """Send Slack notification when webhook task completes."""
    if not os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true":
        return False
    
    from core.slack_client import slack_client
    
    status_emoji = "✅" if success else "❌"
    status_text = "Completed" if success else "Failed"
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{status_emoji} *Task {status_text}*\n*Source:* {webhook_source.title()}\n*Command:* {command}\n*Task ID:* `{task_id}`"
            }
        }
    ]
    
    if success and result:
        result_preview = result[:500] + "..." if len(result) > 500 else result
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Result:*\n```{result_preview}```"
            }
        })
    
    if error:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error:*\n```{error}```"
            }
        })
    
    channel = os.getenv("SLACK_NOTIFICATION_CHANNEL", "#ai-agent-activity")
    text = f"{status_emoji} Task {status_text} - {webhook_source.title()} - {command}"
    
    try:
        await slack_client.post_message(
            channel=channel,
            text=text,
            blocks=blocks
        )
        logger.info("slack_notification_sent", task_id=task_id, success=success)
        return True
    except Exception as e:
        logger.error("slack_notification_failed", task_id=task_id, error=str(e))
        return False
