"""
Jira webhook utility functions.
Signature verification, command matching, task creation, and immediate responses.
"""

import hmac
import hashlib
import os
import json
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Any
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
from api.webhooks.jira.models import TaskSummary

logger = structlog.get_logger()


def _safe_string(value: Any, default: str = "") -> str:
    """
    Safely convert a value to a string.
    
    Handles cases where Jira webhook fields might be lists or other non-string types.
    
    Args:
        value: Value to convert (can be str, list, dict, None, etc.)
        default: Default value to return if value is None or empty
        
    Returns:
        String representation of the value
    """
    if value is None:
        return default
    
    if isinstance(value, str):
        return value
    
    if isinstance(value, list):
        if not value:
            return default
        return " ".join(str(item) for item in value if item)
    
    return str(value) if value else default


def extract_jira_comment_text(comment_body: Any) -> str:
    """
    Extract plain text from Jira comment body.
    
    Handles both plain string format and ADF (Atlassian Document Format).
    
    Args:
        comment_body: Comment body as string, dict (ADF), list, or None
        
    Returns:
        Plain text string extracted from comment body
    """
    if comment_body is None:
        return ""
    
    if isinstance(comment_body, str):
        return comment_body
    
    if isinstance(comment_body, list):
        text_parts = []
        for item in comment_body:
            text_parts.append(extract_jira_comment_text(item))
        return " ".join(text_parts)
    
    if isinstance(comment_body, dict):
        if comment_body.get("type") == "text" and "text" in comment_body:
            return comment_body.get("text", "")
        
        if "content" in comment_body:
            return extract_jira_comment_text(comment_body.get("content"))
        
        if "text" in comment_body:
            return str(comment_body.get("text", ""))
    
    return str(comment_body) if comment_body else ""


def _truncate_text(text: str, max_length: int = 2000) -> str:
    """Truncate text at a natural break point (sentence or line)."""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    truncate_at = max(last_period, last_newline)
    
    if truncate_at > max_length * 0.8:
        truncated = truncated[:truncate_at + 1]
    
    return truncated + "\n\n_(message truncated)_"


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
    ai_agent_name = _safe_string(settings.jira_ai_agent_name or os.getenv("JIRA_AI_AGENT_NAME", "AI Agent"))
    
    changelog = payload.get("changelog", {})
    if changelog:
        items = changelog.get("items", [])
        for item in items:
            if item.get("field") == "assignee":
                to_value = _safe_string(item.get("toString", ""))
                if to_value and ai_agent_name.lower() in to_value.lower():
                    issue_key = payload.get("issue", {}).get("key", "unknown")
                    logger.info("jira_assignee_changed_to_ai", issue_key=issue_key, new_assignee=to_value)
                    return True
    
    if event_type in ["jira:issue_created", "issue_created"]:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        if assignee:
            if isinstance(assignee, dict):
                assignee_name = _safe_string(assignee.get("displayName", "")) or _safe_string(assignee.get("name", ""))
            else:
                assignee_name = _safe_string(assignee)
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
        comment_body = extract_jira_comment_text(payload.get("comment", {}).get("body", ""))
        has_comment_with_agent = bool(comment_body)
        
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


async def is_agent_posted_jira_comment(comment_id: Optional[str]) -> bool:
    """
    Check if comment ID was posted by the agent.
    Returns True to SKIP processing (prevent infinite loops).
    
    Args:
        comment_id: Jira comment ID
    
    Returns:
        True if this comment was posted by agent (should be skipped), False otherwise
    """
    if not comment_id:
        return False
    
    try:
        key = f"jira:posted_comment:{comment_id}"
        exists = await redis_client.exists(key)
        if exists:
            logger.debug("jira_skipped_posted_comment", comment_id=comment_id)
            return True
    except Exception as e:
        logger.warning("jira_redis_check_failed", comment_id=comment_id, error=str(e))
    
    return False


async def is_agent_own_jira_account(account_id: Optional[str]) -> bool:
    """
    Check if comment is from the agent's own Jira account.
    Returns True to SKIP processing (prevent infinite loops).
    
    Args:
        account_id: Jira account ID (e.g., "557058:abc123def456")
    
    Returns:
        True if this is the agent's own account (should be skipped), False otherwise
    """
    if not account_id:
        return False
    
    configured_account_id = settings.jira_account_id
    if not configured_account_id:
        return False
    
    if account_id == configured_account_id:
        logger.debug("jira_skipped_own_account", account_id=account_id)
        return True
    
    return False


async def match_jira_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match Jira webhook payload to a command."""
    from core.command_matcher import extract_command

    comment = payload.get("comment", {})
    author = comment.get("author", {})
    author_type = _safe_string(author.get("accountType", ""))
    author_name = _safe_string(author.get("displayName", ""))

    if author_type == "app" or (author_name and "bot" in author_name.lower()):
        logger.info("jira_skipped_bot_comment", author=author_name, author_type=author_type)
        return None

    # Check if comment was posted by agent (prevent infinite loops)
    comment_id = comment.get("id")
    if comment_id and await is_agent_posted_jira_comment(str(comment_id)):
        logger.info(
            "jira_skipped_posted_comment",
            comment_id=comment_id,
            event_type=event_type
        )
        return None

    # Check if comment is from agent's own Jira account
    account_id = author.get("accountId")
    if account_id and await is_agent_own_jira_account(account_id):
        logger.info(
            "jira_skipped_own_account",
            account_id=account_id,
            event_type=event_type
        )
        return None

    text = ""
    is_comment_event = bool(comment)

    if comment:
        text = extract_jira_comment_text(comment.get("body", ""))

    if not text:
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        text = fields.get("description", "") or fields.get("summary", "")

    if is_assignee_changed_to_ai(payload, event_type):
        if JIRA_WEBHOOK is None:
            logger.warning("jira_webhook_config_missing")
            return None
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

    if not isinstance(command_name, str):
        logger.warning(
            "jira_command_name_not_string",
            command_name=command_name,
            command_name_type=type(command_name).__name__
        )
        return None
    
    command_name_lower = command_name.lower()

    if JIRA_WEBHOOK is None:
        logger.warning("jira_webhook_config_missing")
        return None

    for cmd in JIRA_WEBHOOK.commands:
        if cmd.name.lower() == command_name_lower:
            return cmd
        for alias in cmd.aliases:
            if isinstance(alias, str) and alias.lower() == command_name_lower:
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

    from api.webhooks.common.utils import get_template_content
    template_content = get_template_content(command, "jira")

    if not template_content:
        raise ValueError(f"No template found for command: {command.name}")

    base_message = render_template(template_content, payload, task_id=task_id)
    
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


def extract_pr_url(text: str) -> Optional[str]:
    """Extract PR URL from text if present."""
    if not text:
        return None

    # Defensive type conversion to prevent TypeError with regex
    if isinstance(text, list):
        text = " ".join(str(item) for item in text if item)
    elif not isinstance(text, str):
        text = str(text) if text else ""

    if not text:
        return None

    url_match = re.search(r'https://github\.com/[^/\s]+/[^/\s]+/(?:pull|pulls)/\d+', text, re.IGNORECASE)
    if url_match:
        return url_match.group(0)

    return None


def extract_pr_routing(pr_url: str):
    """Extract repo and PR number from PR URL."""
    from api.webhooks.jira.models import PRRouting

    if not pr_url:
        return None

    # Defensive type conversion to prevent TypeError with regex
    if isinstance(pr_url, list):
        pr_url = " ".join(str(item) for item in pr_url if item)
    elif not isinstance(pr_url, str):
        pr_url = str(pr_url) if pr_url else ""

    if not pr_url:
        return None

    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/(?:pull|pulls)/(\d+)', pr_url, re.IGNORECASE)
    if match:
        owner, repo_name, pr_number = match.groups()
        return PRRouting(
            repo=f"{owner}/{repo_name}",
            pr_number=int(pr_number)
        )

    return None


async def post_jira_task_comment(
    issue: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    pr_url: Optional[str] = None
) -> bool:
    """Post a comment to Jira after task completion."""
    try:
        from api.webhooks.jira.models import JiraTaskCommentRequest
        
        request = JiraTaskCommentRequest(
            issue=issue,
            message=message,
            success=success,
            cost_usd=cost_usd,
            pr_url=pr_url
        )
        
        issue_key = request.get_issue_key()
        
        if not issue_key:
            logger.warning("jira_post_task_comment_no_issue_key", issue_keys=list(issue.keys()))
            return False
        
        pr_url = request.pr_url or extract_pr_url(request.message)
        
        formatted_message = request.message
        
        if pr_url and request.success:
            formatted_message = f"{formatted_message}\n\n🔗 *Pull Request:* {pr_url}"
        
        max_length = 8000
        if len(formatted_message) > max_length:
            truncated_message = formatted_message[:max_length]
            last_period = truncated_message.rfind(".")
            last_newline = truncated_message.rfind("\n")
            truncate_at = max(last_period, last_newline)
            if truncate_at > max_length * 0.8:
                truncated_message = truncated_message[:truncate_at + 1]
            formatted_message = truncated_message + "\n\n... (message truncated)"
        
        if request.success and request.cost_usd > 0:
            formatted_message += f"\n\n💰 Cost: ${request.cost_usd:.4f}"
        
        response = await jira_client.post_comment(issue_key, formatted_message)
        
        # Track comment ID in Redis to prevent infinite loops
        if response and isinstance(response, dict):
            comment_id = response.get("id")
            if comment_id:
                try:
                    key = f"jira:posted_comment:{comment_id}"
                    await redis_client._client.setex(key, 3600, "1")
                    logger.debug("jira_comment_id_tracked", comment_id=comment_id)
                except Exception as e:
                    logger.warning("jira_comment_id_tracking_failed", comment_id=comment_id, error=str(e))
        
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
    error: Optional[str] = None,
    pr_url: Optional[str] = None,
    payload: Optional[dict] = None,
    cost_usd: float = 0.0,
    user_request: Optional[str] = None,
    ticket_key: Optional[str] = None
) -> bool:
    """Send Slack notification when webhook task completes."""
    if not os.getenv("SLACK_NOTIFICATIONS_ENABLED", "true").lower() == "true":
        return False
    
    from core.slack_client import slack_client
    from api.webhooks.slack.utils import extract_task_summary
    from core.webhook_configs import JIRA_WEBHOOK
    from api.webhooks.jira.models import SlackNotificationRequest
    
    request = SlackNotificationRequest(
        task_id=task_id,
        webhook_source=webhook_source,
        command=command,
        success=success,
        result=result,
        error=error,
        pr_url=pr_url,
        payload=payload,
        cost_usd=cost_usd,
        user_request=user_request,
        ticket_key=ticket_key
    )
    
    pr_url = request.pr_url
    if not pr_url and request.result:
        pr_url = extract_pr_url(request.result)
    
    routing = {}
    if request.payload:
        routing = request.payload.get("routing", {})
    
    if not pr_url and routing:
        repo = routing.get("repo")
        pr_number = routing.get("pr_number")
        if repo and pr_number:
            pr_url = f"https://github.com/{repo}/pull/{pr_number}"
    
    if pr_url and not routing:
        pr_routing = extract_pr_routing(pr_url)
        if pr_routing:
            routing = {"repo": pr_routing.repo, "pr_number": pr_routing.pr_number}
    
    status_emoji = "✅" if request.success else "❌"
    status_text = "Completed" if request.success else "Failed"
    
    task_metadata = {"classification": "SIMPLE"}
    summary = extract_task_summary(request.result or "", task_metadata) if request.result else TaskSummary(summary="Task completed")
    
    if not summary.summary and request.result:
        summary.summary = request.result[:200] + "..." if len(request.result) > 200 else request.result
    
    requires_approval = False
    if request.command and JIRA_WEBHOOK is not None:
        for cmd in JIRA_WEBHOOK.commands:
            if cmd.name == request.command:
                requires_approval = cmd.requires_approval
                break
    
    blocks = []
    
    header_text = f"{status_emoji} Task {status_text}"
    if request.ticket_key and request.ticket_key != "unknown":
        header_text += f" - {request.ticket_key}"
    header_text += f" - {summary.classification}"
    
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": header_text
        }
    })
    
    if request.ticket_key and request.ticket_key != "unknown":
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Ticket:* {request.ticket_key}"
            }
        })
    
    if request.user_request:
        user_request_display = request.user_request[:300] + "..." if len(request.user_request) > 300 else request.user_request
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*User Request:*\n{user_request_display}"
            }
        })
    
    if summary.summary:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary*\n{summary.summary}"
            }
        })
    
    if summary.what_was_done:
        what_was_done_text = _truncate_text(summary.what_was_done)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*What Was Done*\n{what_was_done_text}"
            }
        })
    
    if summary.key_insights:
        insights_text = _truncate_text(summary.key_insights)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key Insights*\n{insights_text}"
            }
        })
    
    if request.error:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error:*\n```{request.error[:1000]}```"
            }
        })
    
    if pr_url:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔗 *Pull Request:* {pr_url}"
            }
        })
        
        if requires_approval and routing:
            button_value = {
                "original_task_id": request.task_id,
                "command": request.command,
                "source": request.webhook_source,
                "routing": routing
            }
            
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📄 View Plan"
                        },
                        "url": pr_url,
                        "action_id": "view_pr"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve"
                        },
                        "style": "primary",
                        "action_id": "approve_task",
                        "value": json.dumps({**button_value, "action": "approve"})
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject"
                        },
                        "style": "danger",
                        "action_id": "reject_task",
                        "value": json.dumps({**button_value, "action": "reject"})
                    }
                ]
            })
    
    context_elements = []
    if request.cost_usd > 0:
        context_elements.append({
            "type": "mrkdwn",
            "text": f"💰 Cost: ${request.cost_usd:.4f}"
        })
    context_elements.append({
        "type": "mrkdwn",
        "text": f"Task ID: `{request.task_id}`"
    })
    
    blocks.append({
        "type": "context",
        "elements": context_elements
    })
    
    if request.success:
        channel = os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")
    else:
        channel = os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors")
    text = f"{status_emoji} Task {status_text} - {request.webhook_source.title()} - {request.command}"
    
    try:
        await slack_client.post_message(
            channel=channel,
            text=text,
            blocks=blocks
        )
        logger.info("slack_notification_sent", task_id=request.task_id, success=request.success, channel=channel)
        return True
    except Exception as e:
        error_msg = str(e)
        if "channel_not_found" in error_msg.lower():
            env_var = "SLACK_CHANNEL_AGENTS" if request.success else "SLACK_CHANNEL_ERRORS"
            logger.warning(
                "slack_notification_channel_not_found",
                task_id=request.task_id,
                channel=channel,
                message=f"Slack notification skipped - channel does not exist. Set {env_var} to a valid channel or create the channel."
            )
        else:
            logger.error("slack_notification_failed", task_id=request.task_id, channel=channel, error=error_msg)
        return False
