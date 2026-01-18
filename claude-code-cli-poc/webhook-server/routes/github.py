"""
GitHub Webhook Handler
======================
Handles incoming webhooks from GitHub.
Specifically listens for PR comments that approve the plan for execution.
"""

import hmac
import hashlib
import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from shared.config import get_settings
from webhook_server.queue import get_queue

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("")
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_github_event: str | None = Header(None),
):
    """
    Handle GitHub webhook events.
    
    Triggered when:
    - PR comment contains approval keyword (@agent approve, /approve, LGTM)
    """
    settings = get_settings()
    body = await request.body()
    
    # Validate signature if secret is configured
    if settings.github.webhook_secret and x_hub_signature_256:
        expected = hmac.new(
            settings.github.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(f"sha256={expected}", x_hub_signature_256):
            logger.warning("Invalid GitHub webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse GitHub webhook payload", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    logger.info(
        "Received GitHub webhook",
        event=x_github_event,
        action=payload.get("action"),
    )
    
    # We only care about issue_comment and pull_request_review_comment events
    if x_github_event not in ["issue_comment", "pull_request_review_comment"]:
        return {"status": "ignored", "reason": f"Event {x_github_event} not handled"}
    
    # Check if this is a comment on a PR
    action = payload.get("action", "")
    if action != "created":
        return {"status": "ignored", "reason": "Only new comments are processed"}
    
    # Get PR info
    issue = payload.get("issue", {})
    pull_request = payload.get("pull_request") or issue.get("pull_request")
    
    if not pull_request:
        return {"status": "ignored", "reason": "Comment is not on a PR"}
    
    # Get comment body
    comment = payload.get("comment", {})
    comment_body = comment.get("body", "").lower().strip()
    
    # Check if comment contains approval pattern
    approval_patterns = settings.webhook.approval_pattern_list
    is_approval = any(pattern in comment_body for pattern in approval_patterns)
    
    if not is_approval:
        return {"status": "ignored", "reason": "Comment is not an approval"}
    
    # Extract repo and PR info
    repo = payload.get("repository", {})
    repo_name = repo.get("full_name", "")
    pr_number = issue.get("number") or pull_request.get("number")
    pr_url = pull_request.get("html_url") or issue.get("html_url")
    pr_head_ref = pull_request.get("head", {}).get("ref") if isinstance(pull_request, dict) else None
    
    logger.info(
        "PR approval detected",
        repo=repo_name,
        pr_number=pr_number,
        comment_by=comment.get("user", {}).get("login"),
    )
    
    # Queue task for executor agent
    queue = get_queue()
    task_data = {
        "source": "github",
        "repo": repo_name,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "branch": pr_head_ref,
        "approved_by": comment.get("user", {}).get("login"),
        "comment_url": comment.get("html_url"),
    }
    
    queue.enqueue_executor_task(task_data)
    
    return {
        "status": "queued",
        "repo": repo_name,
        "pr_number": pr_number,
        "message": "Task queued for executor agent",
    }
