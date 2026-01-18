"""
Jira Webhook Handler
====================
Handles incoming webhooks from Jira.
"""

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from shared.config import get_settings
from shared.utils import validate_webhook_signature
from webhook_server.queue import get_queue

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("")
async def handle_jira_webhook(
    request: Request,
    x_atlassian_webhook_identifier: str | None = Header(None),
):
    """
    Handle Jira webhook events.
    
    Triggered when:
    - Issue created with AI-Fix label
    - Issue updated to add AI-Fix label
    """
    settings = get_settings()
    body = await request.body()
    
    # Validate signature if secret is configured
    if settings.jira.webhook_secret:
        # Jira uses different signature headers depending on setup
        # This is a simplified validation
        pass  # TODO: Add proper Jira signature validation
    
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Failed to parse Jira webhook payload", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Extract event type
    webhook_event = payload.get("webhookEvent", "")
    issue = payload.get("issue", {})
    issue_key = issue.get("key", "")
    fields = issue.get("fields", {})
    
    logger.info(
        "Received Jira webhook",
        event=webhook_event,
        issue_key=issue_key,
    )
    
    # Check if this is an issue we should process
    labels = fields.get("labels", [])
    ai_label = settings.jira.ai_label
    
    if ai_label not in labels:
        logger.debug("Issue does not have AI label, ignoring", issue_key=issue_key)
        return {"status": "ignored", "reason": f"No {ai_label} label"}
    
    # Only process issue created or updated events
    if webhook_event not in ["jira:issue_created", "jira:issue_updated"]:
        logger.debug("Ignoring event type", event=webhook_event)
        return {"status": "ignored", "reason": f"Event type {webhook_event} not handled"}
    
    # Queue task for planning agent
    queue = get_queue()
    task_data = {
        "source": "jira",
        "ticket_id": issue_key,
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "priority": fields.get("priority", {}).get("name", "Medium"),
        "labels": labels,
    }
    
    queue.enqueue_planning_task(task_data)
    
    return {
        "status": "queued",
        "ticket_id": issue_key,
        "message": "Task queued for planning agent",
    }
