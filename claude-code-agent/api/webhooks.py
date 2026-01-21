"""Webhook endpoints."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from core.database import get_session
from core.database.models import TaskDB, SessionDB
from core.database.redis_client import redis_client
from shared import TaskStatus, AgentType

logger = structlog.get_logger()

router = APIRouter()


@router.post("/github")
async def github_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Handle GitHub webhooks."""
    try:
        payload = await request.json()
        event_type = request.headers.get("X-GitHub-Event", "unknown")

        logger.info("GitHub webhook received", event=event_type)

        # Handle different event types
        if event_type == "issue_comment":
            return await handle_issue_comment(payload, session)
        elif event_type == "pull_request":
            return await handle_pull_request(payload, session)
        elif event_type == "issues":
            return await handle_issue(payload, session)
        else:
            logger.info("Unhandled GitHub event", event=event_type)
            return {"status": "ignored", "event": event_type}

    except Exception as e:
        logger.error("GitHub webhook error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def handle_issue_comment(payload: dict, session: AsyncSession):
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
        session.add(session_db)

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
        session.add(task_db)
        await session.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("Task created from GitHub comment", task_id=task_id)

        return {"status": "task_created", "task_id": task_id}

    return {"status": "no_action"}


async def handle_pull_request(payload: dict, session: AsyncSession):
    """Handle pull request event."""
    action = payload.get("action")
    pr = payload.get("pull_request", {})

    logger.info(
        "Pull request event",
        action=action,
        pr_number=pr.get("number")
    )

    # TODO: Implement PR handling logic
    return {"status": "received", "action": action}


async def handle_issue(payload: dict, session: AsyncSession):
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
        session.add(session_db)

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
        session.add(task_db)
        await session.commit()

        # Push to queue
        await redis_client.push_task(task_id)

        logger.info("Task created from GitHub issue", task_id=task_id)

        return {"status": "task_created", "task_id": task_id}

    return {"status": "received", "action": action}


@router.post("/jira")
async def jira_webhook(request: Request):
    """Handle Jira webhooks."""
    payload = await request.json()
    logger.info("Jira webhook received", event=payload.get("webhookEvent"))
    return {"status": "received"}


@router.post("/sentry")
async def sentry_webhook(request: Request):
    """Handle Sentry webhooks."""
    payload = await request.json()
    logger.info("Sentry webhook received")
    return {"status": "received"}
