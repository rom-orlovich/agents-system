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

logger = structlog.get_logger()
router = APIRouter()


COMPLETION_HANDLER = "api.webhooks.github.routes.handle_github_task_completion"


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
    """
    Handle GitHub task completion callback.
    
    Called by task worker when task completes.
    
    Actions:
    1. Format message (add emoji for errors)
    2. Post comment to GitHub PR/issue with task result
    3. Send Slack notification (if enabled)
    
    Returns:
        True if comment posted successfully, False otherwise
    """
    if not success and error:
        formatted_message = f"❌ {error}"
    else:
        formatted_message = message
    
    comment_posted = await post_github_task_comment(
        payload=payload,
        message=formatted_message,
        success=success,
        cost_usd=cost_usd
    )
    
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
        
        logger.info("github_webhook_received", event_type=event_type, repo=repo_info, issue_number=issue_number)
        
        validation_result = validate_github_webhook(payload)
        if not validation_result.is_valid:
            logger.info(
                "github_webhook_rejected_by_validation",
                event_type=event_type,
                repo=repo_info,
                issue_number=issue_number,
                reason=validation_result.error_message
            )
            return {"status": "rejected", "actions": 0, "message": "Does not meet activation rules"}
        
        command = match_github_command(payload, event_type)
        if not command:
            logger.warning("github_no_command_matched", event_type=event_type, repo=repo_info, issue_number=issue_number)
            return {"status": "received", "actions": 0, "message": "No command matched"}
        
        immediate_response_sent = await send_github_immediate_response(payload, command, event_type)
        
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
        
        logger.info("github_webhook_processed", task_id=task_id, command=command.name, event_type=event_type, repo=repo_info, issue_number=issue_number)
        
        return {
            "status": "processed",
            "task_id": task_id,
            "command": command.name,
            "immediate_response_sent": immediate_response_sent,
            "completion_handler": COMPLETION_HANDLER
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
