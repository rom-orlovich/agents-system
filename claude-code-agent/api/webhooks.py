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
from shared import TaskStatus, AgentType

logger = structlog.get_logger()

router = APIRouter()


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
            input_message=f"GitHub Issue #{issue.get('number')}: {comment_body}",
            source="webhook",
            source_metadata=str({
                "provider": "github",
                "event": "issue_comment",
                "issue_number": issue.get("number"),
                "comment_id": comment.get("id"),
            }),
        )
        db.add(task_db)
        await db.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("task_created_from_github_comment", task_id=task_id)

        return {"status": "task_created", "task_id": task_id}

    return {"status": "no_action"}


async def handle_pull_request(payload: dict, db: AsyncSession):
    """Handle pull request event."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    logger.info(
        "pull_request_event_received",
        action=action,
        pr_number=pr.get("number")
    )

    # TODO: Implement PR handling logic
    return {"status": "received", "action": action}


async def handle_issue(payload: dict, db: AsyncSession):
    """Handle issue event."""
    action = payload.get("action")
    issue = payload.get("issue", {})

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
            input_message=f"Analyze issue: {issue.get('title')}\n\n{issue.get('body', '')}",
            source="webhook",
            source_metadata=str({
                "provider": "github",
                "event": "issues",
                "action": "opened",
                "issue_number": issue.get("number"),
            }),
        )
        db.add(task_db)
        await db.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("task_created_from_github_issue", task_id=task_id)

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
