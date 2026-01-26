"""
Slack webhook utility functions.
Signature verification, command matching, task creation, and immediate responses.
"""

import hmac
import hashlib
import os
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Optional
import structlog

from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database.models import SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import SLACK_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from core.slack_client import slack_client
from core.routing_metadata import extract_slack_metadata
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType

logger = structlog.get_logger()


async def verify_slack_signature(request: Request, body: bytes) -> None:
    """Verify Slack webhook signature."""
    secret = os.getenv("SLACK_WEBHOOK_SECRET") or settings.slack_webhook_secret
    if not secret:
        logger.warning("SLACK_WEBHOOK_SECRET not configured, skipping verification")
        return
    
    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")
    
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=401, detail="Request timestamp too old")
    
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    expected_signature = "v0=" + hmac.new(
        secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


async def send_slack_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    """Send immediate response to Slack."""
    try:
        if payload.get("type") == "url_verification":
            return True
        
        event = payload.get("event", {})
        channel = event.get("channel")
        user = event.get("user")
        text = event.get("text", "")
        
        if channel and user:
            try:
                await slack_client.post_ephemeral(
                    channel=channel,
                    user=user,
                    text="👀 I received your request. Processing now..."
                )
                logger.info("slack_ephemeral_sent", channel=channel, user=user)
                return True
            except Exception as e:
                logger.warning("slack_ephemeral_failed", channel=channel, user=user, error=str(e))
                return False
        
        return False
        
    except Exception as e:
        logger.error("slack_immediate_response_error", error=str(e))
        return False


def match_slack_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match Slack webhook payload to a command."""
    from core.command_matcher import extract_command

    event = payload.get("event", {})

    if event.get("bot_id") or event.get("subtype") == "bot_message":
        logger.info("slack_skipped_bot_message", bot_id=event.get("bot_id"))
        return None

    text = event.get("text", "")

    result = extract_command(text)
    if result is None:
        logger.debug("slack_no_agent_command", text_preview=text[:100] if text else "")
        return None

    command_name, user_content = result
    payload["_user_content"] = user_content
    for cmd in SLACK_WEBHOOK.commands:
        if cmd.name.lower() == command_name:
            return cmd
        for alias in cmd.aliases:
            if alias.lower() == command_name:
                return cmd

    logger.warning("slack_command_not_configured", command=command_name)
    return None


async def create_slack_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession,
    completion_handler: str
) -> str:
    """Create a task from Slack webhook."""
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
    
    routing = extract_slack_metadata(payload)

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
            "webhook_source": "slack",
            "webhook_name": SLACK_WEBHOOK.name,
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
    external_id = generate_external_id("slack", payload)
    flow_id = generate_flow_id(external_id)
    
    source_metadata = json.loads(task_db.source_metadata or "{}")
    source_metadata["flow_id"] = flow_id
    source_metadata["external_id"] = external_id
    task_db.source_metadata = json.dumps(source_metadata)
    task_db.flow_id = flow_id
    
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("slack_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
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
            "slack_claude_tasks_sync_failed",
            task_id=task_id,
            error=str(sync_error)
        )
    
    await db.commit()
    
    await redis_client.push_task(task_id)
    
    logger.info("slack_task_created", task_id=task_id, command=command.name)
    
    return task_id


async def post_github_comment(repo: str, pr_number: int, comment: str) -> bool:
    """Post a comment to a GitHub PR."""
    from core.github_client import github_client
    
    try:
        owner, repo_name = repo.split("/", 1)
        await github_client.post_pr_comment(
            repo_owner=owner,
            repo_name=repo_name,
            pr_number=pr_number,
            comment_body=comment
        )
        logger.info("github_comment_posted", repo=repo, pr_number=pr_number)
        return True
    except ValueError as e:
        logger.warning("github_client_not_configured", error=str(e))
        return False
    except Exception as e:
        logger.error("github_comment_failed", repo=repo, pr_number=pr_number, error=str(e))
        return False


async def update_slack_message(channel: str, ts: str, text: str) -> bool:
    """Update the original Slack message to show action taken."""
    try:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            }
        ]
        await slack_client.update_message(
            channel=channel,
            timestamp=ts,
            text=text,
            blocks=blocks
        )
        return True
    except ValueError as e:
        logger.warning("slack_client_not_configured", error=str(e))
        return False
    except Exception as e:
        logger.error("slack_message_update_failed", error=str(e))
        return False


async def post_slack_task_comment(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0
) -> bool:
    """Post a message to Slack after task completion."""
    try:
        event = payload.get("event", {})
        channel = event.get("channel")
        thread_ts = event.get("ts")
        
        if not channel:
            logger.warning("slack_post_task_comment_no_channel", payload_keys=list(payload.keys()))
            return False
        
        if success:
            formatted_message = f"✅ {message}"
        else:
            formatted_message = f"❌ {message}"
        
        max_length = 4000
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
        
        await slack_client.post_message(
            channel=channel,
            text=formatted_message,
            thread_ts=thread_ts
        )
        logger.info("slack_task_comment_posted", channel=channel)
        return True
        
    except Exception as e:
        logger.error("slack_post_task_comment_error", error=str(e))
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
