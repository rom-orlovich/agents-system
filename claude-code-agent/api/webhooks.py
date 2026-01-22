"""Webhook endpoints."""

import hmac
import hashlib
import uuid
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from core.config import settings
from core.database import get_session as get_db_session
from core.database.models import TaskDB, SessionDB
from core.database.redis_client import redis_client
from core.github_client import github_client
from shared import TaskStatus, AgentType

logger = structlog.get_logger()

router = APIRouter()


def extract_repo_info(payload: dict) -> tuple[str, str]:
    """Extract repository owner and name from GitHub payload."""
    repo = payload.get("repository", {})
    full_name = repo.get("full_name", "")
    if "/" in full_name:
        owner, name = full_name.split("/", 1)
        return owner, name
    return "", ""


async def verify_github_signature(request: Request, x_hub_signature_256: str | None = Header(None)):
    """Verify GitHub webhook HMAC signature."""
    if not settings.github_webhook_secret:
        # If no secret configured, skip verification (development mode)
        logger.warning("github_webhook_secret_not_configured", warning="Skipping HMAC verification")
        return

    if not x_hub_signature_256:
        logger.error("github_webhook_missing_signature")
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")

    # Read body for HMAC calculation
    body = await request.body()

    # Calculate expected signature
    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Verify signature (constant-time comparison)
    if not hmac.compare_digest(f"sha256={expected}", x_hub_signature_256):
        logger.error("github_webhook_invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    logger.debug("github_webhook_signature_verified")


@router.post("/github")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    _: None = Depends(verify_github_signature)
):
    """
    Handle GitHub webhooks with HMAC signature verification.

    Security: Verifies X-Hub-Signature-256 header against configured secret.
    """
    try:
        payload = await request.json()
        event_type = request.headers.get("X-GitHub-Event", "unknown")

        logger.info("github_webhook_received", event_type=event_type)

        # Handle different event types
        if event_type == "issue_comment":
            return await handle_issue_comment(payload, db)
        elif event_type == "pull_request":
            return await handle_pull_request(payload, db)
        elif event_type == "issues":
            return await handle_issue(payload, db)
        else:
            logger.info("unhandled_github_event", event_type=event_type)
            return {"status": "ignored", "event": event_type}

    except Exception as e:
        logger.error("github_webhook_error", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def handle_issue_comment(payload: dict, db: AsyncSession):
    """Handle issue comment event."""
    action = payload.get("action")
    comment = payload.get("comment", {})
    issue = payload.get("issue", {})
    comment_body = comment.get("body", "")
    comment_id = comment.get("id")
    issue_number = issue.get("number")

    # Extract repo info
    repo_owner, repo_name = extract_repo_info(payload)

    # Check for @agent command
    if "@agent" in comment_body:
        # Create task for planning agent
        task_id = f"task-{uuid.uuid4().hex[:12]}"

        # Create webhook session
        webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
        session_db = SessionDB(
            session_id=webhook_session_id,
            user_id="github-webhook",
            machine_id="claude-agent-001",
            connected_at=datetime.utcnow(),
        )
        db.add(session_db)

        # Create task
        task_db = TaskDB(
            task_id=task_id,
            session_id=webhook_session_id,
            user_id="github-webhook",
            assigned_agent="planning",
            agent_type=AgentType.PLANNING,
            status=TaskStatus.QUEUED,
            input_message=f"GitHub Issue #{issue_number}: {comment_body}",
            source="webhook",
            source_metadata=str({
                "provider": "github",
                "event": "issue_comment",
                "issue_number": issue_number,
                "comment_id": comment_id,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
            }),
        )
        db.add(task_db)
        await db.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("task_created_from_github_comment", task_id=task_id)

        # Post acknowledgment comment back to GitHub
        try:
            if repo_owner and repo_name:
                # Add reaction to original comment
                await github_client.add_reaction(
                    repo_owner,
                    repo_name,
                    comment_id,
                    "eyes"
                )
                
                # Post acknowledgment comment
                ack_message = (
                    f"👋 I've received your request and created task `{task_id}`.\n\n"
                    f"I'll analyze this and get back to you shortly!"
                )
                await github_client.post_issue_comment(
                    repo_owner,
                    repo_name,
                    issue_number,
                    ack_message
                )
                
                logger.info("github_acknowledgment_posted", task_id=task_id)
        except Exception as e:
            logger.error("failed_to_post_github_comment", error=str(e))
            # Don't fail the webhook if comment posting fails

        return {"status": "task_created", "task_id": task_id}

    return {"status": "no_action"}


async def handle_pull_request(payload: dict, db: AsyncSession):
    """Handle pull request event."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title")
    pr_body = pr.get("body", "")

    # Extract repo info
    repo_owner, repo_name = extract_repo_info(payload)

    logger.info(
        "pull_request_event_received",
        action=action,
        pr_number=pr_number
    )

    # Handle PR opened event
    if action == "opened":
        task_id = f"task-{uuid.uuid4().hex[:12]}"

        # Create webhook session
        webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
        session_db = SessionDB(
            session_id=webhook_session_id,
            user_id="github-webhook",
            machine_id="claude-agent-001",
            connected_at=datetime.utcnow(),
        )
        db.add(session_db)

        # Create task for executor agent to review PR
        task_db = TaskDB(
            task_id=task_id,
            session_id=webhook_session_id,
            user_id="github-webhook",
            assigned_agent="executor",
            agent_type=AgentType.EXECUTOR,
            status=TaskStatus.QUEUED,
            input_message=f"Review PR: {pr_title}\n\n{pr_body}",
            source="webhook",
            source_metadata=str({
                "provider": "github",
                "event": "pull_request",
                "action": "opened",
                "pr_number": pr_number,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
            }),
        )
        db.add(task_db)
        await db.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("task_created_from_pr", task_id=task_id)

        # Post acknowledgment comment
        try:
            if repo_owner and repo_name:
                ack_message = (
                    f"🔍 **PR Review Started**\n\n"
                    f"I've created task `{task_id}` to review this pull request.\n\n"
                    f"I'll analyze the changes and provide feedback. "
                    f"Mention me with `@agent` for specific questions!"
                )
                await github_client.post_pr_comment(
                    repo_owner,
                    repo_name,
                    pr_number,
                    ack_message
                )
                
                logger.info("github_pr_acknowledged", task_id=task_id)
        except Exception as e:
            logger.error("failed_to_acknowledge_pr", error=str(e))

        return {"status": "task_created", "task_id": task_id}

    return {"status": "received", "action": action}


async def handle_issue(payload: dict, db: AsyncSession):
    """Handle issue event."""
    action = payload.get("action")
    issue = payload.get("issue", {})
    issue_number = issue.get("number")
    issue_title = issue.get("title")
    issue_body = issue.get("body", "")

    # Extract repo info
    repo_owner, repo_name = extract_repo_info(payload)

    # Auto-create planning task for new issues
    if action == "opened":
        task_id = f"task-{uuid.uuid4().hex[:12]}"

        # Create webhook session
        webhook_session_id = f"webhook-{uuid.uuid4().hex[:12]}"
        session_db = SessionDB(
            session_id=webhook_session_id,
            user_id="github-webhook",
            machine_id="claude-agent-001",
            connected_at=datetime.utcnow(),
        )
        db.add(session_db)

        # Create task
        task_db = TaskDB(
            task_id=task_id,
            session_id=webhook_session_id,
            user_id="github-webhook",
            assigned_agent="planning",
            agent_type=AgentType.PLANNING,
            status=TaskStatus.QUEUED,
            input_message=f"Analyze issue: {issue_title}\n\n{issue_body}",
            source="webhook",
            source_metadata=str({
                "provider": "github",
                "event": "issues",
                "action": "opened",
                "issue_number": issue_number,
                "repo_owner": repo_owner,
                "repo_name": repo_name,
            }),
        )
        db.add(task_db)
        await db.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("task_created_from_github_issue", task_id=task_id)

        # Post acknowledgment comment
        try:
            if repo_owner and repo_name:
                ack_message = (
                    f"🤖 **Automated Analysis Started**\n\n"
                    f"I've created task `{task_id}` to analyze this issue.\n\n"
                    f"I'll review the details and provide insights shortly. "
                    f"Feel free to mention me with `@agent` if you have specific questions!"
                )
                await github_client.post_issue_comment(
                    repo_owner,
                    repo_name,
                    issue_number,
                    ack_message
                )
                
                # Add label to track bot-processed issues
                await github_client.update_issue_labels(
                    repo_owner,
                    repo_name,
                    issue_number,
                    ["bot-processing"]
                )
                
                logger.info("github_issue_acknowledged", task_id=task_id)
        except Exception as e:
            logger.error("failed_to_acknowledge_issue", error=str(e))

        return {"status": "task_created", "task_id": task_id}

    return {"status": "received", "action": action}


@router.post("/jira")
async def jira_webhook(request: Request):
    """Handle Jira webhooks."""
    payload = await request.json()
    logger.info("jira_webhook_received", webhook_event=payload.get("webhookEvent"))
    return {"status": "received"}


@router.post("/sentry")
async def sentry_webhook(request: Request):
    """Handle Sentry webhooks."""
    payload = await request.json()
    logger.info("sentry_webhook_received")
    return {"status": "received"}
