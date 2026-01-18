"""Jira webhook routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from config import settings
from models import TaskSource
from queue import RedisQueue

router = APIRouter()
queue = RedisQueue()


class JiraWebhookPayload(BaseModel):
    """Jira webhook payload model."""
    issue: dict


@router.post("/")
async def jira_webhook(payload: JiraWebhookPayload):
    """Handle Jira webhook events.

    Args:
        payload: Jira webhook payload

    Returns:
        Response dict
    """
    try:
        issue = payload.issue
        issue_key = issue.get("key")
        fields = issue.get("fields", {})
        labels = fields.get("labels", [])

        # Only process issues with AI-Fix label
        if "AI-Fix" not in labels:
            return {"status": "ignored", "reason": "Missing AI-Fix label"}

        # Extract task information
        task_data = {
            "source": TaskSource.JIRA.value,
            "description": fields.get("summary", ""),
            "issue_key": issue_key,
            "repository": None  # Will be discovered by planning agent
        }

        # Add to planning queue
        task_id = await queue.push(settings.PLANNING_QUEUE, task_data)

        print(f"📥 Jira task queued: {task_id} (Issue: {issue_key})")

        return {
            "status": "queued",
            "task_id": task_id,
            "issue_key": issue_key
        }

    except Exception as e:
        print(f"Error processing Jira webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_jira_webhook():
    """Test endpoint for Jira webhook."""
    return {"status": "Jira webhook endpoint is working"}
