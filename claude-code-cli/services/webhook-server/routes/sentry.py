"""Sentry webhook routes."""

import sys
from pathlib import Path
from fastapi import APIRouter, Request
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.config import settings
from shared.models import TaskSource
from shared.task_queue import RedisQueue

router = APIRouter()
queue = RedisQueue()
logger = logging.getLogger("sentry-webhook")


def extract_sentry_tags(event_data: dict) -> dict:
    """Helper to convert Sentry tag list to a dictionary."""
    tags = event_data.get("tags", [])
    # Sentry tags can be a list of lists: [['key', 'value'], ...] or a list of dicts
    if isinstance(tags, list):
        result = {}
        for tag in tags:
            if isinstance(tag, list) and len(tag) >= 2:
                result[tag[0]] = tag[1]
            elif isinstance(tag, dict) and "key" in tag and "value" in tag:
                result[tag["key"]] = tag["value"]
        return result
    return tags


@router.post("/")
async def sentry_webhook(request: Request):
    """Handle Sentry webhook events."""
    payload = await request.json()
    
    # Sentry Issue Alert payload structure: payload["data"]["event"]
    event_data = payload.get("data", {}).get("event", {})
    
    # 1. Extract the tags
    tags = extract_sentry_tags(event_data)
    
    # 2. Extract our custom 'repository' tag
    repository = tags.get("repository", "unknown/repo")

    # 3. Create the task data for the queue
    task_data = {
        "source": TaskSource.SENTRY.value,
        "description": event_data.get("message") or payload.get("title") or "Sentry error",
        "sentry_issue_id": payload.get("id"),
        "repository": repository
    }

    # Add to planning queue
    task_id = await queue.push(settings.PLANNING_QUEUE, task_data)

    print(f"📥 Sentry task queued: {task_id} for repo: {repository}")

    return {"status": "queued", "task_id": task_id}


@router.get("/test")
async def test_sentry_webhook():
    """Test endpoint."""
    return {"status": "Sentry webhook endpoint is working"}
