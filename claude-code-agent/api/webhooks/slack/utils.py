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
from typing import Optional, Any
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


def extract_slack_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    
    if isinstance(value, str):
        return value
    
    if isinstance(value, list):
        if not value:
            return default
        return " ".join(str(item) for item in value if item)
    
    if isinstance(value, dict):
        if "text" in value:
            return str(value.get("text", default))
        if "body" in value:
            return extract_slack_text(value.get("body"), default)
        if "content" in value:
            return extract_slack_text(value.get("content"), default)
    
    return str(value) if value else default


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
        event.get("text", "")
        
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


async def is_agent_posted_slack_message(message_ts: Optional[str]) -> bool:
    """
    Check if message timestamp was posted by the agent.
    Returns True to SKIP processing (prevent infinite loops).
    
    Args:
        message_ts: Slack message timestamp (e.g., "1234567890.123456")
    
    Returns:
        True if this message was posted by agent (should be skipped), False otherwise
    """
    if not message_ts:
        return False
    
    try:
        key = f"slack:posted_message:{message_ts}"
        exists = await redis_client.exists(key)
        if exists:
            logger.debug("slack_skipped_posted_message", message_ts=message_ts)
            return True
    except Exception as e:
        logger.warning("slack_redis_check_failed", message_ts=message_ts, error=str(e))
    
    return False


async def is_agent_own_slack_app(app_id: Optional[str], bot_id: Optional[str]) -> bool:
    """
    Check if message is from the agent's own Slack app.
    Returns True to SKIP processing (prevent infinite loops).
    
    Args:
        app_id: Slack app ID
        bot_id: Slack bot ID
    
    Returns:
        True if this is the agent's own Slack app (should be skipped), False otherwise
    """
    if not app_id:
        return False
    
    configured_app_id = settings.slack_app_id
    if not configured_app_id:
        return False
    
    if app_id == configured_app_id:
        logger.debug("slack_skipped_own_app", app_id=app_id)
        return True
    
    return False


async def match_slack_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match Slack webhook payload to a command."""
    from core.command_matcher import extract_command

    event = payload.get("event", {})

    if event.get("bot_id") or event.get("subtype") == "bot_message":
        logger.info("slack_skipped_bot_message", bot_id=event.get("bot_id"))
        return None

    # Check if message was posted by agent (prevent infinite loops)
    message_ts = event.get("ts")
    if message_ts and await is_agent_posted_slack_message(message_ts):
        logger.info(
            "slack_skipped_posted_message",
            message_ts=message_ts,
            event_type=event_type
        )
        return None

    # Check if message is from agent's own Slack app
    app_id = event.get("app_id") or payload.get("api_app_id")
    bot_id = event.get("bot_id")
    if await is_agent_own_slack_app(app_id, bot_id):
        logger.info(
            "slack_skipped_own_app",
            app_id=app_id,
            bot_id=bot_id,
            event_type=event_type
        )
        return None

    text_raw = event.get("text", "")
    text = extract_slack_text(text_raw)

    result = extract_command(text)
    if result is None:
        logger.debug("slack_no_agent_command", text_preview=text[:100] if text else "")
        return None

    command_name, user_content = result
    payload["_user_content"] = user_content
    
    if not isinstance(command_name, str):
        logger.warning(
            "slack_command_name_not_string",
            command_name=command_name,
            command_name_type=type(command_name).__name__
        )
        return None
    
    command_name_lower = command_name.lower()

    from core.webhook_utils import get_webhook_commands
    commands = get_webhook_commands(SLACK_WEBHOOK, "slack")
    if not commands:
        return None

    for cmd in commands:
        if cmd.name.lower() == command_name_lower:
            return cmd
        for alias in cmd.aliases:
            if isinstance(alias, str) and alias.lower() == command_name_lower:
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

    from api.webhooks.common.utils import get_template_content
    template_content = get_template_content(command, "slack")

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


def build_task_completion_blocks(
    summary: dict,
    routing: dict,
    requires_approval: bool,
    task_id: str,
    cost_usd: float = 0.0,
    command: str = "",
    source: str = "slack"
) -> list:
    """
    Build Slack Block Kit blocks for task completion message.
    
    Args:
        summary: Dict with summary, what_was_done, key_insights, classification
        routing: Dict with routing info (channel, thread_ts, repo, pr_number, ticket_key)
        requires_approval: Whether to show Approve/Review/Reject buttons
        task_id: Task ID
        cost_usd: Task cost in USD
        command: Command name
        source: Source webhook (github, jira, slack)
    
    Returns:
        List of Block Kit blocks
    """
    import json
    
    blocks = []
    
    # Header block
    classification = summary.classification if hasattr(summary, 'classification') else summary.get('classification', 'SIMPLE')
    classification_emoji = {
        "WORKFLOW": "🔄",
        "SIMPLE": "✅",
        "CUSTOM": "⚙️"
    }.get(classification, "✅")
    
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{classification_emoji} Task Completed - {classification}"
        }
    })
    
    # Summary section
    summary_text = summary.summary if hasattr(summary, 'summary') else summary.get("summary")
    if summary_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary*\n{summary_text}"
            }
        })
    
    # What Was Done section
    what_was_done_text = summary.what_was_done if hasattr(summary, 'what_was_done') else summary.get("what_was_done")
    if what_was_done_text:
        max_length = 2000
        
        if len(what_was_done_text) > max_length:
            truncated = what_was_done_text[:max_length]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            truncate_at = max(last_period, last_newline)
            if truncate_at > max_length * 0.8:
                truncated = truncated[:truncate_at + 1]
            what_was_done_text = truncated + "\n\n_(message truncated)_"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*What Was Done*\n{what_was_done_text}"
            }
        })
    
    # Key Insights section
    insights_text = summary.key_insights if hasattr(summary, 'key_insights') else summary.get("key_insights")
    if insights_text:
        max_length = 2000
        
        if len(insights_text) > max_length:
            truncated = insights_text[:max_length]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            truncate_at = max(last_period, last_newline)
            if truncate_at > max_length * 0.8:
                truncated = truncated[:truncate_at + 1]
            insights_text = truncated + "\n\n_(message truncated)_"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key Insights*\n{insights_text}"
            }
        })
    
    # Actions block with buttons (if approval required)
    if requires_approval:
        button_value = {
            "original_task_id": task_id,
            "command": command,
            "source": source,
            "routing": {
                "channel": routing.get("channel"),
                "thread_ts": routing.get("thread_ts"),
                "repo": routing.get("repo"),
                "pr_number": routing.get("pr_number"),
                "ticket_key": routing.get("ticket_key")
            }
        }
        
        blocks.append({
            "type": "actions",
            "elements": [
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
                        "text": "👀 Review"
                    },
                    "action_id": "review_task",
                    "value": json.dumps({**button_value, "action": "review"})
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
    
    # Context block with cost and task ID
    context_elements = []
    if cost_usd > 0:
        context_elements.append({
            "type": "mrkdwn",
            "text": f"💰 Cost: ${cost_usd:.4f}"
        })
    context_elements.append({
        "type": "mrkdwn",
        "text": f"Task ID: `{task_id}`"
    })
    
    blocks.append({
        "type": "context",
        "elements": context_elements
    })
    
    return blocks


def extract_task_summary(result: str, task_metadata: dict):
    """
    Extract structured task summary from result string.

    Args:
        result: Task result string (may contain markdown sections)
        task_metadata: Task metadata dict (may contain classification)

    Returns:
        TaskSummary model with summary, what_was_done, key_insights, classification
    """
    from api.webhooks.jira.models import TaskSummary
    import re

    # Handle list input by converting to string
    if isinstance(result, list):
        result = "\n".join(str(item) for item in result)
    elif not isinstance(result, str):
        result = str(result)

    summary_text = ""
    what_was_done_text = ""
    key_insights_text = ""

    # Try to extract sections from markdown
    summary_match = re.search(r'##\s*Summary\s*\n(.*?)(?=\n##|\Z)', result, re.DOTALL | re.IGNORECASE)
    if summary_match:
        summary_text = summary_match.group(1).strip()
    
    what_was_done_match = re.search(r'##\s*What\s+Was\s+Done\s*\n(.*?)(?=\n##|\Z)', result, re.DOTALL | re.IGNORECASE)
    if what_was_done_match:
        what_was_done_text = what_was_done_match.group(1).strip()
    
    key_insights_match = re.search(r'##\s*Key\s+Insights\s*\n(.*?)(?=\n##|\Z)', result, re.DOTALL | re.IGNORECASE)
    if key_insights_match:
        key_insights_text = key_insights_match.group(1).strip()
    
    # If no sections found, use entire result as summary
    if not summary_text and not what_was_done_text and not key_insights_text:
        summary_text = result.strip()
    
    # Determine classification
    classification = task_metadata.get("classification", "SIMPLE")
    
    # Infer classification from content if not provided
    if classification == "SIMPLE" and (summary_match or what_was_done_match or key_insights_match):
        classification = "WORKFLOW"
    
    return TaskSummary(
        summary=summary_text,
        what_was_done=what_was_done_text if what_was_done_text else None,
        key_insights=key_insights_text if key_insights_text else None,
        classification=classification
    )


async def post_slack_task_comment(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    blocks: Optional[list] = None
) -> bool:
    """Post a message to Slack after task completion."""
    try:
        event = payload.get("event", {})
        channel = event.get("channel")
        thread_ts = event.get("ts")
        
        if not channel:
            logger.warning("slack_post_task_comment_no_channel", payload_keys=list(payload.keys()))
            return False
        
        # Use Block Kit blocks if provided, otherwise use plain text
        if blocks:
            response = await slack_client.post_message(
                channel=channel,
                text=message[:200] if message else "Task completed",  # Fallback text for notifications
                thread_ts=thread_ts,
                blocks=blocks
            )
        else:
            # Fallback to plain text formatting
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
            
            response = await slack_client.post_message(
                channel=channel,
                text=formatted_message,
                thread_ts=thread_ts
            )
        
        # Track message timestamp in Redis to prevent infinite loops
        if response and isinstance(response, dict):
            posted_message_ts = response.get("ts") or response.get("message", {}).get("ts")
            if posted_message_ts:
                try:
                    key = f"slack:posted_message:{posted_message_ts}"
                    await redis_client._client.setex(key, 3600, "1")
                    logger.debug("slack_message_ts_tracked", message_ts=posted_message_ts)
                except Exception as e:
                    logger.warning("slack_message_ts_tracking_failed", message_ts=posted_message_ts, error=str(e))
        
        logger.info("slack_task_comment_posted", channel=channel, used_blocks=blocks is not None)
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
    
    if success:
        channel = os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")
    else:
        channel = os.getenv("SLACK_CHANNEL_ERRORS", "#ai-agent-errors")
    text = f"{status_emoji} Task {status_text} - {webhook_source.title()} - {command}"
    
    try:
        await slack_client.post_message(
            channel=channel,
            text=text,
            blocks=blocks
        )
        logger.info("slack_notification_sent", task_id=task_id, success=success, channel=channel)
        return True
    except Exception as e:
        error_msg = str(e)
        if "channel_not_found" in error_msg.lower():
            env_var = "SLACK_CHANNEL_AGENTS" if success else "SLACK_CHANNEL_ERRORS"
            logger.warning(
                "slack_notification_channel_not_found",
                task_id=task_id,
                channel=channel,
                message=f"Slack notification skipped - channel does not exist. Set {env_var} to a valid channel or create the channel."
            )
        else:
            logger.error("slack_notification_failed", task_id=task_id, channel=channel, error=error_msg)
        return False


async def create_task_from_button_action(
    action: str,
    routing: dict,
    source: str,
    original_task_id: str,
    command: str,
    db: AsyncSession,
    user_name: str = "unknown"
) -> Optional[str]:
    """
    Create a new task from a button action (approve/review/reject).
    
    Args:
        action: Action type (approve, review, reject)
        routing: Routing information (repo/pr_number for GitHub, ticket_key for Jira, channel/thread_ts for Slack)
        source: Source webhook (github, jira, slack)
        original_task_id: Original task ID that triggered the button
        command: Original command name
        db: Database session
        user_name: User who clicked the button
    
    Returns:
        New task ID if created successfully, None otherwise
    """
    try:
        if source == "github":
            from api.webhooks.github.utils import create_github_task
            from core.webhook_configs import GITHUB_WEBHOOK
            from core.webhook_utils import get_webhook_commands

            # Find the command
            commands = get_webhook_commands(GITHUB_WEBHOOK, "github")
            if not commands:
                logger.error("github_webhook_config_missing", action=action)
                return None

            webhook_command = None
            for cmd in commands:
                if cmd.name == action:
                    webhook_command = cmd
                    break

            if not webhook_command:
                logger.warning("github_command_not_found", action=action)
                return None
            
            # Create GitHub payload
            repo = routing.get("repo", "")
            pr_number = routing.get("pr_number")
            if not repo or not pr_number:
                logger.warning("github_routing_missing", routing=routing)
                return None
            
            owner, repo_name = repo.split("/", 1) if "/" in repo else (repo, "")
            
            payload = {
                "action": "created",
                "comment": {
                    "body": f"@agent {action}\n\n_Triggered via Slack by @{user_name}_",
                    "user": {"login": user_name}
                },
                "issue": {
                    "number": pr_number,
                    "pull_request": {}
                },
                "repository": {
                    "full_name": repo,
                    "name": repo_name,
                    "owner": {
                        "login": owner
                    }
                },
                "provider": "github"
            }
            
            task_id = await create_github_task(
                webhook_command,
                payload,
                db,
                completion_handler="api.webhooks.github.routes.handle_github_task_completion"
            )
            logger.info("github_task_created_from_button", action=action, task_id=task_id, pr_number=pr_number)
            return task_id
            
        elif source == "jira":
            from api.webhooks.jira.utils import create_jira_task
            from core.webhook_configs import JIRA_WEBHOOK
            from core.webhook_utils import get_webhook_commands

            # Find the command
            commands = get_webhook_commands(JIRA_WEBHOOK, "jira")
            if not commands:
                logger.error("jira_webhook_config_missing", action=action)
                return None

            webhook_command = None
            for cmd in commands:
                if cmd.name == action:
                    webhook_command = cmd
                    break

            if not webhook_command:
                logger.warning("jira_command_not_found", action=action)
                return None
            
            # Create Jira payload
            ticket_key = routing.get("ticket_key")
            if not ticket_key:
                logger.warning("jira_routing_missing", routing=routing)
                return None
            
            payload = {
                "webhookEvent": "comment_created",
                "comment": {
                    "body": f"@agent {action}\n\n_Triggered via Slack by @{user_name}_",
                    "author": {
                        "displayName": user_name
                    }
                },
                "issue": {
                    "key": ticket_key,
                    "fields": {
                        "summary": f"Task {action}",
                        "description": ""
                    }
                },
                "provider": "jira"
            }
            
            task_id = await create_jira_task(
                webhook_command,
                payload,
                db,
                completion_handler="api.webhooks.jira.routes.handle_jira_task_completion"
            )
            logger.info("jira_task_created_from_button", action=action, task_id=task_id, ticket_key=ticket_key)
            return task_id
            
        elif source == "slack":
            from core.webhook_utils import get_webhook_commands

            # Find the command
            commands = get_webhook_commands(SLACK_WEBHOOK, "slack")
            if not commands:
                logger.error("slack_webhook_config_missing", action=action)
                return None

            webhook_command = None
            for cmd in commands:
                if cmd.name == action:
                    webhook_command = cmd
                    break

            if not webhook_command:
                logger.warning("slack_command_not_found", action=action)
                return None
            
            # Create Slack payload
            channel = routing.get("channel")
            thread_ts = routing.get("thread_ts")
            if not channel:
                logger.warning("slack_routing_missing", routing=routing)
                return None
            
            payload = {
                "event": {
                    "type": "app_mention",
                    "text": f"@agent {action}",
                    "user": "U000000",
                    "channel": channel,
                    "ts": thread_ts or str(time.time()),
                    "thread_ts": thread_ts
                },
                "provider": "slack"
            }
            
            task_id = await create_slack_task(
                webhook_command,
                payload,
                db,
                completion_handler="api.webhooks.slack.routes.handle_slack_task_completion"
            )
            logger.info("slack_task_created_from_button", action=action, task_id=task_id, channel=channel)
            return task_id
            
        else:
            logger.warning("unknown_source_for_button_action", source=source, action=action)
            return None
            
    except Exception as e:
        logger.error("create_task_from_button_action_error", action=action, source=source, error=str(e), exc_info=True)
        return None
