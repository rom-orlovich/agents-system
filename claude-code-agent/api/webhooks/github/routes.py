from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog
import os

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import GITHUB_WEBHOOK
from api.webhooks.github.validation import validate_github_webhook
from api.webhooks.github.utils import (
    verify_github_signature,
    send_github_immediate_response,
    match_github_command,
    create_github_task,
    send_slack_notification,
)
from api.webhooks.github.handlers import GitHubResponseHandler
from api.webhooks.github.routing import extract_github_routing
from api.webhooks.github.constants import (
    PROVIDER_NAME,
    EVENT_HEADER,
    DEFAULT_EVENT_TYPE,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_RECEIVED,
    MESSAGE_DOES_NOT_MEET_RULES,
    MESSAGE_NO_COMMAND_MATCHED,
    MESSAGE_TASK_QUEUED,
    MESSAGE_IMMEDIATE_RESPONSE_FAILED,
    ERROR_IMMEDIATE_RESPONSE_FAILED,
    REDIS_KEY_PREFIX_POSTED_COMMENT,
)
from core.database.redis_client import redis_client
from api.webhooks.slack.utils import extract_task_summary, build_task_completion_blocks
from core.slack_client import slack_client

logger = structlog.get_logger()
router = APIRouter()


COMPLETION_HANDLER = "api.webhooks.github.routes.handle_github_task_completion"


def _has_meaningful_response(result: str, message: str) -> bool:
    return bool(
        (result and len(result.strip()) > 50) or
        (message and len(message.strip()) > 50 and message.strip() != "❌")
    )


def _format_github_message(message: str, success: bool, cost_usd: float) -> str:
    """Format GitHub message with emoji, cost, and truncation."""
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


async def _track_github_comment(comment_id: int | None) -> None:
    """Track GitHub comment ID in Redis to prevent infinite loops."""
    if comment_id:
        try:
            key = f"{REDIS_KEY_PREFIX_POSTED_COMMENT}{comment_id}"
            await redis_client._client.setex(key, 3600, "1")
            logger.debug("github_comment_id_tracked", comment_id=comment_id)
        except Exception as e:
            logger.warning("github_comment_id_tracking_failed", comment_id=comment_id, error=str(e))


async def _add_error_reaction(payload: dict, task_id: str, error: str) -> None:
    original_comment_id = payload.get("comment", {}).get("id")
    if not original_comment_id:
        return

    repo = payload.get("repository", {})
    owner = repo.get("owner", {}).get("login", "")
    repo_name = repo.get("name", "")

    if not owner or not repo_name:
        logger.warning("github_reaction_skipped_no_repo", task_id=task_id)
        return

    try:
        from core.github_client import github_client
        github_client.token = github_client.token or os.getenv("GITHUB_TOKEN")
        if github_client.token:
            github_client.headers["Authorization"] = f"token {github_client.token}"
            await github_client.add_reaction(owner, repo_name, original_comment_id, reaction="-1")
            logger.info(
                "github_error_reaction_added",
                task_id=task_id,
                comment_id=original_comment_id,
                error_preview=error[:200] if error else None
            )
        else:
            logger.warning("github_reaction_skipped_no_token", comment_id=original_comment_id)
    except Exception as e:
        logger.warning("github_error_reaction_failed", task_id=task_id, comment_id=original_comment_id, error=str(e))


def _get_command_requires_approval(command: str) -> bool:
    if not command:
        return False
    for cmd in GITHUB_WEBHOOK.commands:
        if cmd.name == command:
            return cmd.requires_approval
    return False


async def _send_approval_notification(
    payload: dict,
    task_id: str,
    command: str,
    message: str,
    result: str,
    cost_usd: float
) -> None:
    repo = payload.get("repository", {}).get("full_name", "")
    pr_number = payload.get("pull_request", {}).get("number") or payload.get("issue", {}).get("number")

    routing = {"repo": repo, "pr_number": pr_number}
    task_metadata = {"classification": payload.get("classification", "SIMPLE")}
    summary = extract_task_summary(result or message, task_metadata)

    blocks = build_task_completion_blocks(
        summary=summary,
        routing=routing,
        requires_approval=True,
        task_id=task_id or DEFAULT_EVENT_TYPE,
        cost_usd=cost_usd,
        command=command or "",
        source=PROVIDER_NAME
    )

    channel = payload.get("routing", {}).get("slack_channel") or os.getenv("SLACK_CHANNEL_AGENTS", "#ai-agent-activity")

    try:
        await slack_client.post_message(
            channel=channel,
            text=message[:200] if message else "Task completed",
            blocks=blocks
        )
        logger.info("github_slack_rich_notification_sent", task_id=task_id, channel=channel, has_buttons=True)
    except Exception as e:
        logger.warning("github_slack_rich_notification_failed", task_id=task_id, error=str(e))


async def handle_github_task_completion(
    payload: dict,
    message: str,
    success: bool,
    cost_usd: float = 0.0,
    task_id: str = None,
    command: str = None,
    result: str = None,
    error: str = None
) -> bool:
    has_meaningful = _has_meaningful_response(result, message)

    if not success and error:
        await _add_error_reaction(payload, task_id, error)

        if has_meaningful:
            logger.info("github_task_failed_but_response_already_posted", task_id=task_id, error_preview=error[:200] if error else None)
        else:
            logger.info("github_task_failed_no_new_comment", task_id=task_id, error_preview=error[:200] if error else None)

        comment_posted = False
    else:
        # Extract routing metadata from payload
        routing = extract_github_routing(payload)
        
        # Format message
        formatted_message = _format_github_message(message, success, cost_usd)
        
        # Post using handler
        handler = GitHubResponseHandler()
        try:
            comment_posted, response = await handler.post_response(routing, formatted_message)
            
            # Track comment ID in Redis if available
            if comment_posted and response and isinstance(response, dict):
                comment_id = response.get("id")
                if comment_id:
                    await _track_github_comment(comment_id)
        except Exception as e:
            logger.error("github_handler_post_failed", error=str(e), task_id=task_id)
            comment_posted = False

    if _get_command_requires_approval(command):
        await _send_approval_notification(payload, task_id, command, message, result, cost_usd)

    await send_slack_notification(
        task_id=task_id,
        webhook_source=PROVIDER_NAME,
        command=command,
        success=success,
        result=result,
        error=error
    )

    return comment_posted


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    GitHub webhook endpoint.
    
    Flow:
    1. Get webhook event
    2. Validate webhook
    3. Validate command
    4. Send immediate response (reaction/comment)
    5. Create task (with completion handler registered: handle_github_task_completion)
    6. Put task in queue
    7. Log event
    8. Send back HTTP response
    
    After task completes (task worker calls handle_github_task_completion):
    - handle_github_task_completion() posts comment to GitHub PR/issue
    - handle_github_task_completion() sends Slack notification (if enabled)
    - Task worker updates conversation with result
    """
    repo_info = None
    issue_number = None
    task_id = None
    
    try:
        body = await request.body()
        
        await verify_github_signature(request, body)
        
        payload = json.loads(body.decode())
        payload["provider"] = PROVIDER_NAME
        
        repo = payload.get("repository", {})
        repo_info = f"{repo.get('owner', {}).get('login', 'unknown')}/{repo.get('name', 'unknown')}"
        issue = payload.get("issue") or payload.get("pull_request")
        if issue:
            issue_number = issue.get("number")
        
        event_type = request.headers.get(EVENT_HEADER, DEFAULT_EVENT_TYPE)
        action = payload.get("action", "")
        if action:
            event_type = f"{event_type}.{action}"
        
        logger.info(
            "github_webhook_received",
            event_type=event_type,
            action=payload.get("action"),
            repo=repo_info,
            issue_number=issue_number,
            comment_id=payload.get("comment", {}).get("id"),
            comment_preview=payload.get("comment", {}).get("body", "")[:100] if payload.get("comment") else None
        )
        
        validation_result = validate_github_webhook(payload)
        if not validation_result.is_valid:
            logger.info(
                "github_webhook_rejected_by_validation",
                event_type=event_type,
                action=payload.get("action"),
                repo=repo_info,
                issue_number=issue_number,
                reason=validation_result.error_message,
                comment_preview=payload.get("comment", {}).get("body", "")[:100] if payload.get("comment") else None
            )
            return {"status": STATUS_REJECTED, "actions": 0, "message": MESSAGE_DOES_NOT_MEET_RULES}
        
        command = await match_github_command(payload, event_type)
        if not command:
            logger.warning(
                "github_no_command_matched",
                event_type=event_type,
                action=payload.get("action"),
                repo=repo_info,
                issue_number=issue_number,
                comment_preview=payload.get("comment", {}).get("body", "")[:100] if payload.get("comment") else None
            )
            return {"status": STATUS_RECEIVED, "actions": 0, "message": MESSAGE_NO_COMMAND_MATCHED}
        
        immediate_response_sent = await send_github_immediate_response(payload, command, event_type)
        
        if not immediate_response_sent:
            logger.error(
                "github_immediate_response_failed",
                repo=repo_info,
                issue_number=issue_number,
                event_type=event_type,
                message="Immediate response failed - webhook rejected"
            )
            return {
                "status": STATUS_REJECTED,
                "message": MESSAGE_IMMEDIATE_RESPONSE_FAILED,
                "error": ERROR_IMMEDIATE_RESPONSE_FAILED
            }
        
        task_id = await create_github_task(command, payload, db, completion_handler=COMPLETION_HANDLER)
        logger.info("github_task_created_success", task_id=task_id, repo=repo_info, issue_number=issue_number)
        
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=GITHUB_WEBHOOK.name,
            provider=PROVIDER_NAME,
            event_type=event_type,
            payload_json=json.dumps(payload),
            matched_command=command.name,
            task_id=task_id,
            response_sent=immediate_response_sent,
            created_at=datetime.now(timezone.utc)
        )
        db.add(event_db)
        await db.commit()
        logger.info("github_event_logged", event_id=event_id, task_id=task_id, repo=repo_info, issue_number=issue_number)
        
        logger.info(
            "github_completion_handler_registered",
            task_id=task_id,
            handler=COMPLETION_HANDLER,
            message="Completion handler registered - will be called by task worker when task completes"
        )
        
        logger.info(
            "github_webhook_processed",
            task_id=task_id,
            command=command.name,
            event_type=event_type,
            repo=repo_info,
            issue_number=issue_number,
            immediate_response_sent=immediate_response_sent
        )
        
        return {
            "status": STATUS_ACCEPTED,
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER,
            "message": MESSAGE_TASK_QUEUED
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "github_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
            repo=repo_info,
            issue_number=issue_number,
            task_id=task_id,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
