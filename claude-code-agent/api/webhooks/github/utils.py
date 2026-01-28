import hmac
import hashlib
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
import structlog
import httpx

from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database.models import SessionDB, TaskDB
from core.database.redis_client import redis_client
from core.webhook_configs import GITHUB_WEBHOOK
from core.webhook_engine import render_template, create_webhook_conversation
from core.github_client import github_client
from core.routing_metadata import extract_github_metadata
from shared.machine_models import WebhookCommand
from shared import TaskStatus, AgentType
from api.webhooks.github.constants import (
    SIGNATURE_HEADER,
    SIGNATURE_PREFIX,
    EVENT_ISSUE_COMMENT,
    EVENT_ISSUES,
    EVENT_PULL_REQUEST,
    EVENT_PULL_REQUEST_REVIEW_COMMENT,
    FIELD_REPOSITORY,
    FIELD_OWNER,
    FIELD_LOGIN,
    FIELD_NAME,
    FIELD_COMMENT,
    FIELD_ID,
    FIELD_ISSUE,
    FIELD_NUMBER,
    FIELD_PULL_REQUEST,
    FIELD_BODY,
    FIELD_TITLE,
    REACTION_EYES,
    REDIS_KEY_PREFIX_POSTED_COMMENT,
    REDIS_TTL_POSTED_COMMENT,
    ENV_GITHUB_TOKEN,
    ENV_GITHUB_WEBHOOK_SECRET,
    MESSAGE_ISSUE_RESPONSE,
    MESSAGE_PR_RESPONSE,
    STATUS_CODE_UNAUTHORIZED,
)

logger = structlog.get_logger()


def extract_github_text(value: Any, default: str = "") -> str:
    """
    Safely extract text from GitHub webhook payload fields.
    
    Handles cases where GitHub webhook fields might be lists, dicts, or other non-string types.
    This can happen in edge cases or with certain webhook formats.
    
    Args:
        value: Value to extract text from (can be str, list, dict, None, etc.)
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
        result = " ".join(str(item) for item in value if item)
        return result if isinstance(result, str) else default
    
    if isinstance(value, dict):
        if "text" in value:
            result = str(value.get("text", default))
            return result if isinstance(result, str) else default
        if "body" in value:
            result = extract_github_text(value.get("body"), default)
            return result if isinstance(result, str) else default
        if "content" in value:
            result = extract_github_text(value.get("content"), default)
            return result if isinstance(result, str) else default
    
    result = str(value) if value else default
    return result if isinstance(result, str) else default


async def verify_github_signature(request: Request, body: bytes) -> None:
    signature = request.headers.get(SIGNATURE_HEADER, "")
    secret = os.getenv(ENV_GITHUB_WEBHOOK_SECRET) or settings.github_webhook_secret

    if signature:
        if not secret:
            raise HTTPException(status_code=STATUS_CODE_UNAUTHORIZED, detail="Webhook secret not configured but signature provided")

        if signature.startswith(SIGNATURE_PREFIX):
            signature = signature[len(SIGNATURE_PREFIX):]

        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=STATUS_CODE_UNAUTHORIZED, detail="Invalid signature")
    elif secret:
        logger.warning("github_webhook_secret_no_header")


def _ensure_github_token() -> bool:
    github_client.token = github_client.token or os.getenv(ENV_GITHUB_TOKEN)
    if github_client.token:
        github_client.headers["Authorization"] = f"token {github_client.token}"
    return bool(github_client.token)


async def _send_comment_reaction(owner: str, repo_name: str, comment_id: int, event_type: str) -> bool:
    if not _ensure_github_token():
        logger.warning(
            "github_reaction_skipped_no_token",
            comment_id=comment_id,
            event_type=event_type,
            message="GITHUB_TOKEN not configured - reaction not sent"
        )
        return False

    try:
        reaction_response = await github_client.add_reaction(
            owner, repo_name, comment_id, reaction=REACTION_EYES
        )
        logger.info(
            "github_reaction_sent",
            comment_id=comment_id,
            event_type=event_type,
            reaction_id=reaction_response.get("id") if reaction_response else None,
            reaction_content=reaction_response.get("content") if reaction_response else None
        )
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error(
                "github_reaction_auth_failed",
                comment_id=comment_id,
                status_code=401,
                event_type=event_type,
                message="GitHub authentication failed"
            )
        else:
            logger.warning(
                "github_reaction_failed",
                comment_id=comment_id,
                status_code=e.response.status_code,
                error=str(e),
                event_type=event_type
            )
        return False
    except ValueError as e:
        logger.warning(
            "github_reaction_skipped_no_token",
            comment_id=comment_id,
            error=str(e),
            event_type=event_type,
            message="GITHUB_TOKEN not configured - reaction not sent"
        )
        return False
    except Exception as e:
        logger.warning("github_reaction_failed", comment_id=comment_id, error=str(e), event_type=event_type)
        return False


async def _send_issue_immediate_comment(owner: str, repo_name: str, issue_number: int, event_type: str) -> bool:
    if not _ensure_github_token():
        logger.warning(
            "github_comment_skipped_no_token",
            issue_number=issue_number,
            event_type=event_type,
            message="GITHUB_TOKEN not configured - comment not sent"
        )
        return False

    try:
        await github_client.post_issue_comment(owner, repo_name, issue_number, MESSAGE_ISSUE_RESPONSE)
        logger.info("github_comment_sent", issue_number=issue_number)
        return True
    except Exception as e:
        logger.warning("github_comment_failed", issue_number=issue_number, error=str(e), event_type=event_type)
        return False


async def _send_pr_immediate_comment(owner: str, repo_name: str, pr_number: int, event_type: str) -> bool:
    if not _ensure_github_token():
        logger.warning(
            "github_pr_comment_skipped_no_token",
            pr_number=pr_number,
            event_type=event_type,
            message="GITHUB_TOKEN not configured - comment not sent"
        )
        return False

    try:
        await github_client.post_pr_comment(owner, repo_name, pr_number, MESSAGE_PR_RESPONSE)
        logger.info("github_pr_comment_sent", pr_number=pr_number)
        return True
    except Exception as e:
        logger.warning("github_pr_comment_failed", pr_number=pr_number, error=str(e), event_type=event_type)
        return False


async def send_github_immediate_response(
    payload: dict,
    command: WebhookCommand,
    event_type: str
) -> bool:
    try:
        repo = payload.get(FIELD_REPOSITORY, {})
        owner = repo.get(FIELD_OWNER, {}).get(FIELD_LOGIN, "")
        repo_name = repo.get(FIELD_NAME, "")

        if not owner or not repo_name:
            logger.warning("github_immediate_response_no_repo", payload=payload)
            return False

        if event_type.startswith(EVENT_ISSUE_COMMENT):
            comment_id = payload.get(FIELD_COMMENT, {}).get(FIELD_ID)
            if comment_id:
                return await _send_comment_reaction(owner, repo_name, comment_id, event_type)

        elif event_type.startswith(EVENT_ISSUES):
            issue_number = payload.get("issue", {}).get("number")
            if issue_number:
                return await _send_issue_immediate_comment(owner, repo_name, issue_number, event_type)

        elif event_type.startswith(EVENT_PULL_REQUEST):
            pr_number = payload.get("pull_request", {}).get("number")
            if pr_number:
                return await _send_pr_immediate_comment(owner, repo_name, pr_number, event_type)

        return False

    except Exception as e:
        logger.error("github_immediate_response_error", error=str(e))
        return False


async def is_agent_posted_comment(comment_id: Optional[int]) -> bool:
    """
    Check if comment ID was posted by the agent.
    Returns True to SKIP processing (prevent infinite loops).
    
    Args:
        comment_id: GitHub comment ID
    
    Returns:
        True if this comment was posted by agent (should be skipped), False otherwise
    """
    if not comment_id:
        return False
    
    try:
        key = f"{REDIS_KEY_PREFIX_POSTED_COMMENT}{comment_id}"
        exists = await redis_client.exists(key)
        if exists:
            logger.debug("github_skipped_posted_comment", comment_id=comment_id)
            return True
    except Exception as e:
        logger.warning("github_redis_check_failed", comment_id=comment_id, error=str(e))
    
    return False


async def match_github_command(payload: dict, event_type: str) -> Optional[WebhookCommand]:
    """Match GitHub webhook payload to a command."""
    from core.command_matcher import is_bot_comment, extract_command

    sender = payload.get("sender", {})
    sender_login = sender.get("login", "")
    sender_type = sender.get("type", "")
    
    if is_bot_comment(sender_login, sender_type):
        logger.info(
            "github_skipped_bot_comment",
            sender=sender_login,
            sender_type=sender_type,
            event_type=event_type
        )
        return None
    
    comment_id = None
    if event_type.startswith("issue_comment"):
        comment_id = payload.get("comment", {}).get("id")
        if await is_agent_posted_comment(comment_id):
            logger.info(
                "github_skipped_posted_comment",
                comment_id=comment_id,
                event_type=event_type
            )
            return None
    elif event_type.startswith("pull_request_review_comment"):
        comment_id = payload.get("comment", {}).get("id")
        if await is_agent_posted_comment(comment_id):
            logger.info(
                "github_skipped_posted_pr_review_comment",
                comment_id=comment_id,
                event_type=event_type
            )
            return None

    text = ""
    if event_type.startswith("issue_comment"):
        comment_body = payload.get("comment", {}).get("body", "")
        text = extract_github_text(comment_body)
        logger.debug(
            "github_comment_text_extracted",
            event_type=event_type,
            action=payload.get("action"),
            text_preview=text[:100] if text else "",
            comment_id=comment_id
        )
    elif event_type.startswith("pull_request_review_comment"):
        comment_body = payload.get("comment", {}).get("body", "")
        text = extract_github_text(comment_body)
    elif event_type.startswith(EVENT_ISSUES):
        issue_body = payload.get("issue", {}).get("body", "")
        issue_title = payload.get("issue", {}).get("title", "")
        text = extract_github_text(issue_body) or extract_github_text(issue_title)
    elif event_type.startswith(EVENT_PULL_REQUEST):
        pr_body = payload.get("pull_request", {}).get("body", "")
        pr_title = payload.get("pull_request", {}).get("title", "")
        text = extract_github_text(pr_body) or extract_github_text(pr_title)

    result = extract_command(text)

    if result is None:
        logger.debug(
            "github_no_agent_command",
            event_type=event_type,
            action=payload.get("action"),
            text_preview=text[:100] if text else "",
            sender=sender_login
        )
        return None

    command_name, user_content = result
    
    if not isinstance(command_name, str):
        logger.warning(
            "github_command_name_not_string",
            command_name=command_name,
            command_name_type=type(command_name).__name__
        )
        return None
    
    command_name_lower = command_name.lower()
    
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name.lower() == command_name_lower:
            payload["_user_content"] = user_content
            return cmd
        for alias in cmd.aliases:
            if isinstance(alias, str) and alias.lower() == command_name_lower:
                payload["_user_content"] = user_content
                return cmd

    logger.warning("github_command_not_configured", command=command_name)
    return None


async def create_github_task(
    command: WebhookCommand,
    payload: dict,
    db: AsyncSession,
    completion_handler: str
) -> str:
    """Create a task from GitHub webhook."""
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
    
    routing = extract_github_metadata(payload)

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
            "webhook_source": "github",
            "webhook_name": GITHUB_WEBHOOK.name,
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
    external_id = generate_external_id("github", payload)
    flow_id = generate_flow_id(external_id)
    
    source_metadata = json.loads(task_db.source_metadata or "{}")
    source_metadata["flow_id"] = flow_id
    source_metadata["external_id"] = external_id
    task_db.source_metadata = json.dumps(source_metadata)
    task_db.flow_id = flow_id
    
    conversation_id = await create_webhook_conversation(task_db, db)
    if conversation_id:
        logger.info("github_conversation_created", conversation_id=conversation_id, task_id=task_id)
    
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
            "github_claude_tasks_sync_failed",
            task_id=task_id,
            error=str(sync_error)
        )
    
    await db.commit()
    
    await redis_client.push_task(task_id)
    
    logger.info("github_task_created", task_id=task_id, command=command.name)
    
    return task_id


def _extract_repo_info(payload: dict) -> tuple[str, str]:
    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")
    return owner, repo_name


def _format_github_message(message: str, success: bool, cost_usd: float) -> str:
    if success:
        formatted = f"✅ {message}"
    else:
        formatted = "❌" if message == "❌" else f"❌ {message}"

    max_length = 4000 if success else 8000
    if len(formatted) > max_length:
        truncated = formatted[:max_length]
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")
        truncate_at = max(last_period, last_newline)
        if truncate_at > max_length * 0.8:
            truncated = truncated[:truncate_at + 1]
        formatted = truncated + "\n\n... (message truncated)"

    if success and cost_usd > 0:
        formatted += f"\n\n💰 Cost: ${cost_usd:.4f}"

    return formatted


def _get_github_target(payload: dict) -> tuple[str, Optional[int]]:
    pr = payload.get("pull_request", {})
    issue = payload.get("issue", {})

    if pr and pr.get("number"):
        return "pr", pr.get("number")
    elif issue and issue.get("number"):
        if issue.get("pull_request"):
            return "pr", issue.get("number")
        else:
            return "issue", issue.get("number")
    return "none", None


async def _track_github_comment(comment_id: Optional[int]) -> None:
    if comment_id:
        try:
            key = f"{REDIS_KEY_PREFIX_POSTED_COMMENT}{comment_id}"
            await redis_client._client.setex(key, 3600, "1")
            logger.debug("github_comment_id_tracked", comment_id=comment_id)
        except Exception as e:
            logger.warning("github_comment_id_tracking_failed", comment_id=comment_id, error=str(e))


async def post_github_task_comment(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0
) -> bool:
    try:
        owner, repo_name = _extract_repo_info(payload)

        if not owner or not repo_name:
            logger.debug("github_post_comment_no_repo", payload_keys=list(payload.keys()))
            return False

        formatted_message = _format_github_message(message, success, cost_usd)
        target_type, target_number = _get_github_target(payload)
        comment_id = None

        if target_type == "pr":
            response = await github_client.post_pr_comment(owner, repo_name, target_number, formatted_message)
            comment_id = response.get("id") if isinstance(response, dict) else None
            logger.info("github_pr_comment_posted", pr_number=target_number, comment_id=comment_id)
        elif target_type == "issue":
            response = await github_client.post_issue_comment(owner, repo_name, target_number, formatted_message)
            comment_id = response.get("id") if isinstance(response, dict) else None
            logger.info("github_issue_comment_posted", issue_number=target_number, comment_id=comment_id)
        else:
            logger.warning("github_no_issue_or_pr_found", payload_keys=list(payload.keys()))
            return False

        await _track_github_comment(comment_id)
        return True

    except ValueError as e:
        logger.warning(
            "github_post_task_comment_skipped_no_token",
            error=str(e),
            message="GITHUB_TOKEN not configured - comment not posted"
        )
        return False
    except Exception as e:
        logger.error("github_post_task_comment_error", error=str(e))
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
