"""
GitHub Webhook Routes
Main route handler for GitHub webhooks.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import uuid
from datetime import datetime, timezone
import structlog

from core.database import get_session as get_db_session
from core.database.models import WebhookEventDB
from core.webhook_configs import GITHUB_WEBHOOK
from api.webhooks.github.validation import validate_github_webhook
from api.webhooks.github.utils import (
    verify_github_signature,
    send_github_immediate_response,
    match_github_command,
    create_github_task,
    post_github_task_comment,
    send_slack_notification,
)
from api.webhooks.slack.utils import extract_task_summary, build_task_completion_blocks
from core.slack_client import slack_client
import os

logger = structlog.get_logger()
router = APIRouter()


COMPLETION_HANDLER = "api.webhooks.github.routes.handle_github_task_completion"


def _has_meaningful_response(result: str, message: str) -> bool:
    return bool(
        (result and len(result.strip()) > 50) or
        (message and len(message.strip()) > 50 and message.strip() != "❌")
    )


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
        task_id=task_id or "unknown",
        cost_usd=cost_usd,
        command=command or "",
        source="github"
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
        comment_posted = await post_github_task_comment(
            payload=payload,
            message=message,
            success=success,
            cost_usd=cost_usd
        )

    if _get_command_requires_approval(command):
        await _send_approval_notification(payload, task_id, command, message, result, cost_usd)

    await send_slack_notification(
        task_id=task_id,
        webhook_source="github",
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
        payload["provider"] = "github"
        
        repo = payload.get("repository", {})
        repo_info = f"{repo.get('owner', {}).get('login', 'unknown')}/{repo.get('name', 'unknown')}"
        issue = payload.get("issue") or payload.get("pull_request")
        if issue:
            issue_number = issue.get("number")
        
        event_type = request.headers.get("X-GitHub-Event", "unknown")
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
            return {"status": "rejected", "actions": 0, "message": "Does not meet activation rules"}
        
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
            return {"status": "received", "actions": 0, "message": "No command matched"}
        
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
                "status": "rejected",
                "message": "Failed to send immediate response. Check GITHUB_TOKEN configuration and permissions.",
                "error": "immediate_response_failed"
            }
        
        task_id = await create_github_task(command, payload, db, completion_handler=COMPLETION_HANDLER)
        logger.info("github_task_created_success", task_id=task_id, repo=repo_info, issue_number=issue_number)
        
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        event_db = WebhookEventDB(
            event_id=event_id,
            webhook_id=GITHUB_WEBHOOK.name,
            provider="github",
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
            "status": "accepted",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER,
            "message": "Task queued for processing"
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
